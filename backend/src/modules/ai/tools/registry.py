from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.ai.tools.analytics import AnalyticsTools
from src.modules.ai.tools.chart_generation import ChartGenerationTool
from src.modules.ai.tools.data_access import DataAccessTools
from src.modules.ai.tools.rag import RagTools
from src.modules.ai.tools.reporting import ReportingTools
from src.modules.ai.tools.result import tool_result


APPROVED_TOOL_NAMES = [
    "load_csv_dataset",
    "get_dataset_schema",
    "query_database",
    "preview_dataset",
    "describe_dataset",
    "aggregate_dataset",
    "correlate_dataset",
    "detect_basic_anomalies",
    "generate_chart",
    "search_business_knowledge",
    "create_markdown_report",
]


class ToolRegistry:
    def __init__(
        self,
        session: AsyncSession,
        job_id: int | None = None,
        upload_dir: Path | None = None,
    ) -> None:
        self.session = session
        self.job_id = job_id
        self.data_access = DataAccessTools(session, upload_dir=upload_dir)
        self.analytics = AnalyticsTools(session, upload_dir=upload_dir)
        self.chart_generation = ChartGenerationTool(session, upload_dir=upload_dir, job_id=job_id)
        self.rag = RagTools()
        self.reporting = ReportingTools(session, job_id=job_id)

    def tool_names(self) -> list[str]:
        return list(APPROVED_TOOL_NAMES)

    def tool_definitions_text(self) -> str:
        return "\n".join(
            [
                "load_csv_dataset(dataset_id): load staged CSV metadata; does not return raw rows.",
                "get_dataset_schema(dataset_id): return dataset/table columns and profile metadata.",
                "query_database(dataset_id, sql): run read-only SELECT/WITH SELECT SQL for a DB dataset.",
                "preview_dataset(dataset_id, limit): return a small row preview from CSV or database.",
                "describe_dataset(dataset_id): compute row/column and numeric summary statistics.",
                "aggregate_dataset(dataset_id, group_by, metric, operation): group a metric by a dimension.",
                "correlate_dataset(dataset_id, columns): compute numeric correlation matrix.",
                "detect_basic_anomalies(dataset_id, column): find simple z-score anomalies.",
                "generate_chart(dataset_id, chart_type, x, y, aggregation): create Plotly chart artifact.",
                "search_business_knowledge(query, document_types): search Chroma business knowledge only.",
                "create_markdown_report(title, sections, artifact_ids): create Markdown report artifact.",
            ]
        )

    async def execute(self, tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        tool = self._tool_map().get(tool_name)
        if not tool:
            return tool_result(tool_name, "error", "Tool is not approved")
        try:
            return await tool(**arguments)
        except Exception as exc:
            return tool_result(tool_name, "error", str(exc))

    def _tool_map(self) -> dict[str, Callable[..., Awaitable[dict[str, Any]]]]:
        return {
            "load_csv_dataset": self.data_access.load_csv_dataset,
            "get_dataset_schema": self.data_access.get_dataset_schema,
            "query_database": self.data_access.query_database,
            "preview_dataset": self.data_access.preview_dataset,
            "describe_dataset": self.analytics.describe_dataset,
            "aggregate_dataset": self.analytics.aggregate_dataset,
            "correlate_dataset": self.analytics.correlate_dataset,
            "detect_basic_anomalies": self.analytics.detect_basic_anomalies,
            "generate_chart": self.chart_generation.generate_chart,
            "search_business_knowledge": self.rag.search_business_knowledge,
            "create_markdown_report": self.reporting.create_markdown_report,
        }
