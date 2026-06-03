from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.ai.tools.result import tool_result
from src.modules.api.controllers.artifacts import create_markdown_artifact


class ReportingTools:
    def __init__(self, session: AsyncSession, job_id: int | None = None) -> None:
        self.session = session
        self.job_id = job_id

    async def create_markdown_report(
        self,
        title: str,
        sections: list[str],
        artifact_ids: list[int] | None = None,
    ) -> dict[str, Any]:
        if self.job_id is None:
            return tool_result("create_markdown_report", "error", "Job id is required to create report artifacts")
        content = "\n\n".join(section.strip() for section in sections if section.strip())
        artifact = await create_markdown_artifact(self.session, self.job_id, title, content)
        ids = [*(artifact_ids or []), artifact.id]
        return tool_result(
            "create_markdown_report",
            "ok",
            f"Created report artifact {artifact.id}.",
            {"title": title},
            ids,
        )
