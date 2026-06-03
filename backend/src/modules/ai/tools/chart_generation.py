from pathlib import Path

import pandas as pd
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.config import get_settings
from src.core.models import Artifact, Dataset
from src.modules.api.controllers.artifacts import create_plotly_bar_artifact
from src.modules.ai.tools.result import tool_result
from src.modules.data.loaders.database_introspection import quote_identifier
from src.modules.data.loaders.tabular import aggregate_for_chart, load_uploaded_frame
from src.modules.utils.sql_runner import run_readonly_query


class ChartGenerationTool:
    name = "generate_chart"
    description = "Generate Plotly chart data for the selected dataset and return it as a frontend artifact payload."

    def __init__(self, session: AsyncSession, upload_dir: Path | None = None, job_id: int | None = None) -> None:
        self.session = session
        self.upload_dir = upload_dir or get_settings().upload_dir
        self.job_id = job_id

    async def run(self, job_id: int, dataset: Dataset) -> Artifact | None:
        chart_frame, x_column, y_column = self._chart_frame(dataset)
        if chart_frame is None or not x_column or not y_column:
            return None
        return await create_plotly_bar_artifact(
            self.session,
            job_id=job_id,
            title=f"{dataset.display_name}: {y_column} by {x_column}",
            frame=chart_frame,
            x=x_column,
            y=y_column,
        )

    async def generate_chart(
        self,
        dataset_id: int,
        chart_type: str = "bar",
        x: str | None = None,
        y: str | None = None,
        aggregation: str = "sum",
    ) -> dict:
        if chart_type != "bar":
            return tool_result("generate_chart", "error", "Only bar charts are supported in v1")
        if aggregation not in {"sum", "mean", "count"}:
            return tool_result("generate_chart", "error", "Only sum, mean, and count aggregations are supported in v1")
        dataset = await self.session.get(Dataset, dataset_id)
        if not dataset:
            return tool_result("generate_chart", "error", "Dataset not found")
        if isinstance(x, list):
            return await self._generate_multi_x_chart(dataset, x, y, aggregation)
        chart_frame, x_column, y_column = self._chart_frame(dataset, x=x, y=y, aggregation=aggregation)
        if chart_frame is None or not x_column or not y_column:
            return tool_result("generate_chart", "error", "Dataset needs one dimension and one numeric metric")
        title = self._title(dataset.display_name, x_column, y_column, aggregation)
        artifact = await create_plotly_bar_artifact(
            self.session,
            job_id=self._required_job_id(),
            title=title,
            frame=chart_frame,
            x=x_column,
            y=y_column,
        )
        return tool_result(
            "generate_chart",
            "ok",
            f"Created chart artifact {artifact.id}.",
            {"artifact": {"id": artifact.id, "kind": artifact.kind, "payload": artifact.payload}},
            [artifact.id],
        )

    async def _generate_multi_x_chart(
        self,
        dataset: Dataset,
        x_columns: list[str],
        y_column: str | None,
        aggregation: str,
    ) -> dict:
        if not y_column:
            return tool_result("generate_chart", "error", "A metric column is required for multi-column charts")
        frames = []
        for x_column in x_columns:
            chart_frame, resolved_x, resolved_y = self._chart_frame(dataset, x=x_column, y=y_column, aggregation=aggregation)
            if chart_frame is None or not resolved_x or not resolved_y:
                continue
            frames.append((resolved_x, resolved_y, chart_frame))
        if not frames:
            return tool_result("generate_chart", "error", "No requested room-related columns could be charted")

        title = self._multi_title(dataset.display_name, y_column, aggregation)
        payload = {
            "data": [
                {
                    "type": "bar",
                    "name": x_column,
                    "x": frame[x_column].astype(str).tolist(),
                    "y": frame[y_column].tolist(),
                }
                for x_column, y_column, frame in frames
            ],
            "layout": {
                "title": title,
                "xaxis": {"title": "room-related values"},
                "yaxis": {"title": self._aggregation_label(y_column, aggregation)},
                "barmode": "group",
            },
        }
        artifact = Artifact(
            job_id=self._required_job_id(),
            kind="plotly",
            title=title,
            mime_type="application/json",
            payload=payload,
        )
        self.session.add(artifact)
        await self.session.flush()
        return tool_result(
            "generate_chart",
            "ok",
            f"Created multi-column chart artifact {artifact.id}.",
            {"artifact": {"id": artifact.id, "kind": artifact.kind, "payload": artifact.payload}},
            [artifact.id],
        )

    def _chart_frame(
        self,
        dataset: Dataset,
        x: str | None = None,
        y: str | None = None,
        aggregation: str = "sum",
    ) -> tuple[pd.DataFrame | None, str | None, str | None]:
        columns = dataset.profile.get("columns", {})
        x_column = x or next(
            (name for name, meta in columns.items() if meta.get("semantic_type") in {"categorical", "datetime"}), None
        )
        y_column = y or next((name for name, meta in columns.items() if meta.get("semantic_type") == "numeric"), None)
        if not x_column or not y_column:
            return None, None, None

        if dataset.table_name:
            schema = quote_identifier(dataset.table_schema or "public")
            table = quote_identifier(dataset.table_name)
            x_ident = quote_identifier(x_column)
            y_ident = quote_identifier(y_column)
            if aggregation == "mean":
                metric_sql = f'avg({y_ident}) AS "{y_column}"'
            elif aggregation == "count":
                metric_sql = f'count(*) AS "{y_column}"'
            else:
                metric_sql = f'sum({y_ident}) AS "{y_column}"'
            rows = run_readonly_query(
                f"SELECT {x_ident}, {metric_sql} "
                f"FROM {schema}.{table} GROUP BY {x_ident} ORDER BY \"{y_column}\" DESC LIMIT 20"
            )
            return pd.DataFrame(rows), x_column, y_column

        if dataset.file_name:
            if x and y:
                frame = load_uploaded_frame(self.upload_dir, dataset.file_name)
                if x not in frame.columns or y not in frame.columns:
                    return None, None, None
                if aggregation == "mean":
                    chart_frame = frame.groupby(x, as_index=False)[y].mean()
                elif aggregation == "count":
                    chart_frame = frame.groupby(x, as_index=False).size().rename(columns={"size": y})
                else:
                    chart_frame = frame.groupby(x, as_index=False)[y].sum()
                chart_frame = chart_frame.sort_values(y, ascending=False).head(20)
                return chart_frame, x, y
            return aggregate_for_chart(load_uploaded_frame(self.upload_dir, dataset.file_name), dataset.profile)

        return None, None, None

    def _required_job_id(self) -> int:
        job_id = getattr(self, "job_id", None)
        if job_id is None:
            raise ValueError("Job id is required to create chart artifacts")
        return job_id

    def _title(self, display_name: str, x_column: str, y_column: str, aggregation: str) -> str:
        label = {"sum": y_column, "mean": f"average {y_column}", "count": f"count by {x_column}"}[aggregation]
        if aggregation == "count":
            return f"{display_name}: {label}"
        return f"{display_name}: {label} by {x_column}"

    def _multi_title(self, display_name: str, y_column: str, aggregation: str) -> str:
        return f"{display_name}: {self._aggregation_label(y_column, aggregation)} by room-related fields"

    def _aggregation_label(self, y_column: str, aggregation: str) -> str:
        return {"sum": y_column, "mean": f"average {y_column}", "count": "count"}[aggregation]
