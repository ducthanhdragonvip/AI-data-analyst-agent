from typing import Any, Literal


ToolStatus = Literal["ok", "error"]


def tool_result(
    tool_name: str,
    status: ToolStatus,
    text: str,
    data: dict[str, Any] | None = None,
    artifact_ids: list[int] | None = None,
) -> dict[str, Any]:
    return {
        "tool_name": tool_name,
        "status": status,
        "text": text,
        "data": data or {},
        "artifact_ids": artifact_ids or [],
    }
