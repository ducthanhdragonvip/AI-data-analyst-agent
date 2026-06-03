from src.core.config import get_settings
from src.core.models import Dataset
from src.modules.utils.sql_runner import run_readonly_query


def run_analyst_llm(question: str, context: str) -> str:
    settings = get_settings()
    if not settings.openai_api_key:
        return f"I reviewed the available dataset context.\n\n{context[:1800]}"

    from langchain_core.messages import HumanMessage, SystemMessage
    from langchain_openai import ChatOpenAI

    llm = ChatOpenAI(model=settings.openai_model, api_key=settings.openai_api_key, temperature=0)
    result = llm.invoke(
        [
            SystemMessage(
                content=(
                    "You are an AI data analyst. Answer concisely, cite datasets/tables/columns used, "
                    "and never suggest mutating SQL."
                )
            ),
            HumanMessage(content=f"Context:\n{context}\n\nQuestion:\n{question}"),
        ]
    )
    return str(result.content)


def run_sql_tool(sql: str) -> str:
    return str(run_readonly_query(sql))


def plan_tool_calls(question: str, datasets: list[Dataset], job_type: str) -> list[dict]:
    if not datasets:
        return [{"name": "search_business_knowledge", "arguments": {"query": question, "document_types": []}}]

    question_lower = question.lower()
    dataset = datasets[0]
    calls: list[dict] = []
    if dataset.source_type == "upload" and not dataset.table_name:
        calls.append({"name": "load_csv_dataset", "arguments": {"dataset_id": dataset.id}})
    else:
        calls.append({"name": "get_dataset_schema", "arguments": {"dataset_id": dataset.id}})

    if job_type == "report":
        calls.append({"name": "describe_dataset", "arguments": {"dataset_id": dataset.id}})
        calls.append(
            {
                "name": "create_markdown_report",
                "arguments": {
                    "title": f"{dataset.display_name} analyst report",
                    "sections": [f"# {dataset.display_name} analyst report", "The final analyst answer is saved in the conversation."],
                    "artifact_ids": [],
                },
            }
        )
        return calls

    if any(token in question_lower for token in ("chart", "plot", "graph", "draw", "visual")):
        chart_arguments = {
            "dataset_id": dataset.id,
            "chart_type": "bar",
            "aggregation": _chart_aggregation(question_lower, dataset),
        }
        x_column, y_column = _chart_columns(question_lower, dataset)
        if x_column:
            chart_arguments["x"] = x_column
        if y_column:
            chart_arguments["y"] = y_column
        calls.append(
            {
                "name": "generate_chart",
                "arguments": chart_arguments,
            }
        )
    elif any(token in question_lower for token in ("sum", "total", "average", "mean", "min", "max", "count")):
        calls.append({"name": "describe_dataset", "arguments": {"dataset_id": dataset.id}})
    elif any(token in question_lower for token in ("policy", "sop", "process", "definition", "dictionary")):
        calls.append({"name": "search_business_knowledge", "arguments": {"query": question, "document_types": []}})
    else:
        calls.append({"name": "describe_dataset", "arguments": {"dataset_id": dataset.id}})
    return calls


def _chart_columns(question_lower: str, dataset: Dataset) -> tuple[str | list[str] | None, str | None]:
    columns = dataset.profile.get("columns", {})
    if _asks_for_all_rooms(question_lower):
        room_columns = _room_related_columns(columns)
        y_column = _price_column(columns)
        if room_columns:
            return room_columns, y_column

    matched = [_column_name for _column_name in columns if _mentions_column(question_lower, _column_name)]
    numeric = [name for name, meta in columns.items() if meta.get("semantic_type") == "numeric"]
    dimensions = [
        name
        for name, meta in columns.items()
        if meta.get("semantic_type") in {"categorical", "datetime"} or _looks_like_dimension(name)
    ]

    y_column = next((name for name in matched if _looks_like_metric(name)), None)
    if not y_column:
        y_column = next((name for name in numeric if _looks_like_metric(name) and name in matched), None)
    if not y_column and "price" in question_lower:
        y_column = next((name for name in numeric if "price" in name.lower()), None)

    x_column = next((name for name in matched if name != y_column and (name in dimensions or name in numeric)), None)
    if not x_column and any(token in question_lower for token in ("room", "rooms", "bedroom", "bedrooms")):
        x_column = next((name for name in columns if any(token in name.lower() for token in ("room", "bedroom"))), None)
    if not x_column:
        x_column = next((name for name in dimensions if name != y_column), None)

    return x_column, y_column


def _chart_aggregation(question_lower: str, dataset: Dataset) -> str:
    if any(token in question_lower for token in ("average", "avg", "mean")) or "price" in question_lower:
        return "mean"
    if any(token in question_lower for token in ("demand", "count", "number of", "how many")):
        return "count"
    return "sum"


def _mentions_column(question_lower: str, column_name: str) -> bool:
    normalized = column_name.lower().replace("_", " ")
    terms = {normalized, normalized.rstrip("s"), f"{normalized}s"}
    return any(term and term in question_lower for term in terms)


def _looks_like_dimension(column_name: str) -> bool:
    name = column_name.lower()
    return any(token in name for token in ("room", "bedroom", "bathroom", "year", "month", "date", "type", "category"))


def _looks_like_metric(column_name: str) -> bool:
    name = column_name.lower()
    return any(token in name for token in ("price", "amount", "revenue", "sales", "cost", "value", "total"))


def _asks_for_all_rooms(question_lower: str) -> bool:
    return any(token in question_lower for token in ("all room", "all of the room", "all rooms", "all of rooms"))


def _room_related_columns(columns: dict) -> list[str]:
    return [name for name in columns if "room" in name.lower()]


def _price_column(columns: dict) -> str | None:
    numeric = [name for name, meta in columns.items() if meta.get("semantic_type") == "numeric"]
    return next((name for name in numeric if "price" in name.lower()), None)
