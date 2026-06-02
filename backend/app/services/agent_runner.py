from typing import Any

import pandas as pd
from langchain.agents import AgentExecutor, create_react_agent
from langchain.prompts import PromptTemplate
from langchain.tools import Tool
from langchain_openai import ChatOpenAI
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.config import get_settings
from app.models import Conversation, Dataset, Job, Message
from app.services.artifacts import create_markdown_artifact, create_matplotlib_line_artifact, create_plotly_bar_artifact
from app.services.chroma_service import ChromaProfileStore
from app.services.dataset_profile import profile_to_text
from app.services.sql_runner import run_readonly_query


REACT_PROMPT = PromptTemplate.from_template(
    """You are an AI data analyst. Use the provided tools to inspect dataset context and run read-only analysis.
Always cite the table and columns you used. If the user asks for a chart, describe the chart specification.

Tools:
{tools}

Use this format:
Question: the input question
Thought: what to do next
Action: the action to take, one of [{tool_names}]
Action Input: the input to the action
Observation: the result of the action
... repeat Thought/Action/Action Input/Observation as needed
Thought: I now know the final answer
Final Answer: concise answer with chart/report recommendations when relevant

Conversation and dataset context:
{context}

Question: {input}
{agent_scratchpad}"""
)


class DataAnalystAgent:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.settings = get_settings()
        self.profile_store = ChromaProfileStore()

    async def run_analysis_job(self, job: Job) -> dict[str, Any]:
        payload = job.input
        conversation = await self._conversation(payload.get("conversation_id"), payload.get("message", "Analysis"))
        user_message = Message(
            conversation_id=conversation.id,
            role="user",
            content=payload["message"],
            artifact_ids=[],
        )
        self.session.add(user_message)
        await self.session.flush()

        dataset_ids = payload.get("dataset_ids", [])
        context = await self._context(payload["message"], dataset_ids, conversation.id)
        answer = self._invoke_agent(payload["message"], context)

        artifact_ids = await self._maybe_create_chart(job.id, payload["message"], dataset_ids)
        assistant_message = Message(
            conversation_id=conversation.id,
            role="assistant",
            content=answer,
            artifact_ids=artifact_ids,
        )
        self.session.add(assistant_message)
        await self.session.flush()
        return {"conversation_id": conversation.id, "message": answer, "artifact_ids": artifact_ids}

    async def run_report_job(self, job: Job) -> dict[str, Any]:
        payload = job.input
        conversation = await self._conversation(payload.get("conversation_id"), "Analyst report")
        dataset_ids = payload.get("dataset_ids", [])
        context = await self._context(payload.get("instructions", "Create an analyst report"), dataset_ids, conversation.id)
        report = self._invoke_agent(
            "Create a Markdown analyst report with executive summary, key findings, caveats, and next questions.",
            context,
        )
        artifact = await create_markdown_artifact(self.session, job_id=job.id, title="Analyst report", content=report)
        message = Message(
            conversation_id=conversation.id,
            role="assistant",
            content=f"Generated Markdown report: {artifact.title}",
            artifact_ids=[artifact.id],
        )
        self.session.add(message)
        await self.session.flush()
        return {"conversation_id": conversation.id, "artifact_ids": [artifact.id], "message": message.content}

    async def _conversation(self, conversation_id: int | None, title: str) -> Conversation:
        if conversation_id:
            conversation = await self.session.get(Conversation, conversation_id)
            if conversation:
                return conversation
        conversation = Conversation(title=title[:255] or "New conversation")
        self.session.add(conversation)
        await self.session.flush()
        return conversation

    async def _context(self, question: str, dataset_ids: list[int], conversation_id: int) -> str:
        datasets = await self._datasets(dataset_ids)
        profile_text = "\n\n".join(
            profile_to_text(dataset.display_name, dataset.table_schema, dataset.table_name, dataset.profile)
            for dataset in datasets
        )
        rag_hits = self.profile_store.search(question, dataset_ids=dataset_ids)
        rag_text = "\n\n".join(hit["document"] for hit in rag_hits)
        history_result = await self.session.execute(
            select(Message).where(Message.conversation_id == conversation_id).order_by(Message.created_at.desc()).limit(8)
        )
        history = "\n".join(f"{message.role}: {message.content}" for message in reversed(list(history_result.scalars())))
        return f"Dataset profiles:\n{profile_text}\n\nRAG matches:\n{rag_text}\n\nRecent conversation:\n{history}"

    async def _datasets(self, dataset_ids: list[int]) -> list[Dataset]:
        if not dataset_ids:
            result = await self.session.execute(select(Dataset).order_by(Dataset.created_at.desc()).limit(5))
            return list(result.scalars())
        result = await self.session.execute(select(Dataset).where(Dataset.id.in_(dataset_ids)))
        return list(result.scalars())

    def _invoke_agent(self, question: str, context: str) -> str:
        if not self.settings.openai_api_key:
            raise RuntimeError("OPENAI_API_KEY is required to run the AI analyst agent")

        tools = [
            Tool(
                name="search_dataset_profiles",
                func=lambda text: "\n\n".join(hit["document"] for hit in self.profile_store.search(text)),
                description="Search dataset schema/profile context. Input should be a natural-language question.",
            ),
            Tool(
                name="run_readonly_sql",
                func=lambda sql: str(run_readonly_query(sql)),
                description="Run a single read-only SQL SELECT query against Postgres. Input must be SQL.",
            ),
        ]
        llm = ChatOpenAI(model=self.settings.openai_model, api_key=self.settings.openai_api_key, temperature=0)
        agent = create_react_agent(llm, tools, REACT_PROMPT)
        executor = AgentExecutor(agent=agent, tools=tools, verbose=False, handle_parsing_errors=True, max_iterations=8)
        result = executor.invoke({"input": question, "context": context})
        return str(result.get("output", "No answer returned."))

    async def _maybe_create_chart(self, job_id: int, question: str, dataset_ids: list[int]) -> list[int]:
        if "chart" not in question.lower() and "plot" not in question.lower() and "graph" not in question.lower():
            return []
        datasets = await self._datasets(dataset_ids)
        if not datasets:
            return []
        dataset = datasets[0]
        columns = dataset.profile.get("columns", {})
        x_column = next(
            (
                name
                for name, meta in columns.items()
                if meta.get("semantic_type") in {"categorical", "datetime"}
            ),
            None,
        )
        y_column = next((name for name, meta in columns.items() if meta.get("semantic_type") == "numeric"), None)
        if not x_column or not y_column:
            return []

        if columns[x_column].get("semantic_type") == "datetime":
            sql = (
                f'SELECT date_trunc(\'month\', "{x_column}") AS "{x_column}", '
                f'sum("{y_column}") AS "{y_column}" '
                f'FROM "{dataset.table_name}" GROUP BY 1 ORDER BY 1'
            )
        else:
            sql = (
                f'SELECT "{x_column}", sum("{y_column}") AS "{y_column}" '
                f'FROM "{dataset.table_name}" GROUP BY "{x_column}" ORDER BY "{y_column}" DESC LIMIT 20'
            )
        rows = run_readonly_query(sql)
        if not rows:
            return []
        frame = pd.DataFrame(rows)
        title = f"{dataset.display_name}: {y_column} by {x_column}"
        if "line" in question.lower() or "matplotlib" in question.lower():
            artifact = await create_matplotlib_line_artifact(
                self.session,
                job_id=job_id,
                title=title,
                frame=frame,
                x=x_column,
                y=y_column,
            )
        else:
            artifact = await create_plotly_bar_artifact(
                self.session,
                job_id=job_id,
                title=title,
                frame=frame,
                x=x_column,
                y=y_column,
            )
        return [artifact.id]
