from typing import Any, TypedDict

from src.core.models import Conversation, Dataset, Job


class AnalystState(TypedDict, total=False):
    job: Job
    payload: dict[str, Any]
    conversation: Conversation
    datasets: list[Dataset]
    context: str
    tool_calls: list[dict[str, Any]]
    tool_results: list[dict[str, Any]]
    message: str
    artifact_ids: list[int]
    result: dict[str, Any]
