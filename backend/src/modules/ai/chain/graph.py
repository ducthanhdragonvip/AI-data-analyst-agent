from sqlalchemy.ext.asyncio import AsyncSession

from src.core.models import Conversation, Dataset, Job, Message
from src.modules.ai.agents.analyst import plan_tool_calls, run_analyst_llm
from src.modules.ai.agents.report import run_report_agent
from src.modules.ai.chain.state import AnalystState
from src.modules.ai.context.builder import load_datasets
from src.modules.ai.tools.registry import ToolRegistry


class DataAnalystWorkflow:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def run(self, job: Job) -> dict:
        graph = self._compile_graph()
        state = await graph.ainvoke({"job": job, "payload": job.input})
        return state["result"]

    def _compile_graph(self):
        from langgraph.graph import END, StateGraph

        builder = StateGraph(AnalystState)
        builder.add_node("prepare", self._prepare)
        builder.add_node("llm_plan", self._llm_plan)
        builder.add_node("tools", self._tools)
        builder.add_node("llm_answer", self._llm_answer)
        builder.add_node("persist", self._persist)
        builder.set_entry_point("prepare")
        builder.add_edge("prepare", "llm_plan")
        builder.add_edge("llm_plan", "tools")
        builder.add_edge("tools", "llm_answer")
        builder.add_edge("llm_answer", "persist")
        builder.add_edge("persist", END)
        return builder.compile()

    async def _prepare(self, state: AnalystState) -> AnalystState:
        job = state["job"]
        payload = state["payload"]
        conversation = await self._conversation(payload.get("conversation_id"), payload.get("message") or "Analyst report")
        datasets = await load_datasets(self.session, payload.get("dataset_ids", []))
        context = await self._metadata_context(conversation.id, datasets)
        return {
            **state,
            "conversation": conversation,
            "datasets": datasets,
            "context": context,
            "artifact_ids": [],
            "tool_calls": [],
            "tool_results": [],
        }

    async def _llm_plan(self, state: AnalystState) -> AnalystState:
        job = state["job"]
        payload = state["payload"]
        question = payload.get("message") or payload.get("instructions") or "Create report"
        tool_calls = plan_tool_calls(question, state["datasets"], job.job_type)
        return {**state, "tool_calls": tool_calls}

    async def _tools(self, state: AnalystState) -> AnalystState:
        job = state["job"]
        registry = ToolRegistry(self.session, job_id=job.id)
        results = []
        artifact_ids: list[int] = []
        for call in state["tool_calls"]:
            result = await registry.execute(call["name"], call.get("arguments", {}))
            results.append(result)
            artifact_ids.extend(result.get("artifact_ids", []))
        return {**state, "tool_results": results, "artifact_ids": artifact_ids}

    async def _llm_answer(self, state: AnalystState) -> AnalystState:
        job = state["job"]
        payload = state["payload"]
        question = payload.get("message") or payload.get("instructions") or "Create report"
        tool_context = self._tool_results_context(state["tool_results"])
        context = f"{state['context']}\n\nTool results:\n{tool_context}"
        if job.job_type == "report":
            message = run_report_agent(context, payload.get("instructions"))
        else:
            message = run_analyst_llm(question, context)
        return {**state, "message": message}

    async def _persist(self, state: AnalystState) -> AnalystState:
        job = state["job"]
        payload = state["payload"]
        conversation = state["conversation"]
        if job.job_type == "analysis":
            self.session.add(
                Message(
                    conversation_id=conversation.id,
                    role="user",
                    content=payload["message"],
                    artifact_ids=[],
                )
            )
        self.session.add(
            Message(
                conversation_id=conversation.id,
                role="assistant",
                content=state["message"],
                artifact_ids=state["artifact_ids"],
            )
        )
        await self.session.flush()
        result = {"conversation_id": conversation.id, "message": state["message"], "artifact_ids": state["artifact_ids"]}
        return {**state, "result": result}

    async def _conversation(self, conversation_id: int | None, title: str) -> Conversation:
        if conversation_id:
            conversation = await self.session.get(Conversation, conversation_id)
            if conversation:
                return conversation
        conversation = Conversation(title=(title or "New conversation")[:255])
        self.session.add(conversation)
        await self.session.flush()
        return conversation

    async def _metadata_context(self, conversation_id: int, datasets: list[Dataset]) -> str:
        from sqlalchemy.future import select

        dataset_lines = []
        for dataset in datasets:
            columns = ", ".join(dataset.profile.get("columns", {}).keys()) or "unknown columns"
            source = dataset.table_name or dataset.file_name or dataset.source_type
            dataset_lines.append(
                f"- id={dataset.id}; name={dataset.display_name}; source={source}; rows={dataset.row_count}; columns={columns}"
            )
        messages = await self.session.execute(
            select(Message).where(Message.conversation_id == conversation_id).order_by(Message.created_at.desc()).limit(8)
        )
        history = "\n".join(f"{message.role}: {message.content}" for message in reversed(list(messages.scalars())))
        registry = ToolRegistry(self.session)
        return (
            f"Selected dataset metadata:\n{chr(10).join(dataset_lines) or 'No datasets selected.'}\n\n"
            f"Available tools:\n{registry.tool_definitions_text()}\n\n"
            f"Recent conversation:\n{history or 'No prior messages.'}"
        )

    def _tool_results_context(self, tool_results: list[dict]) -> str:
        lines = []
        for result in tool_results:
            lines.append(
                f"{result['tool_name']} [{result['status']}]: {result['text']}\n"
                f"data={result.get('data', {})}\nartifact_ids={result.get('artifact_ids', [])}"
            )
        return "\n\n".join(lines) or "No tools were called."
