from pathlib import Path
from typing import Any

import pandas as pd
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.config import get_settings
from src.core.models import Dataset
from src.modules.ai.tools.result import tool_result
from src.modules.data.loaders.database_introspection import quote_identifier
from src.modules.data.loaders.tabular import load_uploaded_frame
from src.modules.utils.sql_runner import run_readonly_query


class DataAccessTools:
    def __init__(self, session: AsyncSession, upload_dir: Path | None = None) -> None:
        self.session = session
        self.upload_dir = upload_dir or get_settings().upload_dir

    async def load_csv_dataset(self, dataset_id: int) -> dict[str, Any]:
        dataset = await self._dataset(dataset_id)
        if not dataset:
            return tool_result("load_csv_dataset", "error", "Dataset not found")
        if dataset.source_type != "upload" or not dataset.file_name:
            return tool_result("load_csv_dataset", "error", "Dataset is not a staged CSV upload")
        return tool_result(
            "load_csv_dataset",
            "ok",
            f"Loaded CSV metadata for {dataset.display_name}. Use preview_dataset for sample rows.",
            {
                "dataset_id": dataset.id,
                "display_name": dataset.display_name,
                "row_count": dataset.row_count,
                "columns": list(dataset.profile.get("columns", {}).keys()),
                "profile": dataset.profile,
            },
        )

    async def get_dataset_schema(self, dataset_id: int) -> dict[str, Any]:
        dataset = await self._dataset(dataset_id)
        if not dataset:
            return tool_result("get_dataset_schema", "error", "Dataset not found")
        data = {
            "dataset_id": dataset.id,
            "source_type": dataset.source_type,
            "display_name": dataset.display_name,
            "table_schema": dataset.table_schema,
            "table_name": dataset.table_name,
            "row_count": dataset.row_count,
            "columns": dataset.profile.get("columns", {}),
        }
        return tool_result("get_dataset_schema", "ok", f"Schema loaded for {dataset.display_name}.", data)

    async def query_database(self, dataset_id: int, sql: str) -> dict[str, Any]:
        dataset = await self._dataset(dataset_id)
        if not dataset:
            return tool_result("query_database", "error", "Dataset not found")
        if not dataset.table_name:
            return tool_result("query_database", "error", "Dataset is not imported or registered as a database table")
        try:
            rows = run_readonly_query(sql)
        except ValueError as exc:
            return tool_result("query_database", "error", str(exc))
        return tool_result(
            "query_database",
            "ok",
            f"Query returned {len(rows)} rows.",
            {"rows": rows[:100], "row_count": len(rows), "truncated": len(rows) > 100},
        )

    async def preview_dataset(self, dataset_id: int, limit: int = 20) -> dict[str, Any]:
        dataset = await self._dataset(dataset_id)
        if not dataset:
            return tool_result("preview_dataset", "error", "Dataset not found")
        limit = max(1, min(int(limit), 100))
        if dataset.file_name and not dataset.table_name:
            frame = load_uploaded_frame(self.upload_dir, dataset.file_name).head(limit)
            return tool_result(
                "preview_dataset",
                "ok",
                f"Previewed {len(frame)} rows from {dataset.display_name}.",
                {"rows": self._records(frame), "row_count": len(frame)},
            )
        if dataset.table_name:
            schema = quote_identifier(dataset.table_schema or "public")
            table = quote_identifier(dataset.table_name)
            rows = run_readonly_query(f"SELECT * FROM {schema}.{table} LIMIT {limit}")
            return tool_result(
                "preview_dataset",
                "ok",
                f"Previewed {len(rows)} rows from {dataset.display_name}.",
                {"rows": rows, "row_count": len(rows)},
            )
        return tool_result("preview_dataset", "error", "Dataset has no readable source")

    async def frame_for_dataset(self, dataset_id: int, limit: int | None = None) -> tuple[Dataset | None, pd.DataFrame | None]:
        dataset = await self._dataset(dataset_id)
        if not dataset:
            return None, None
        if dataset.file_name and not dataset.table_name:
            frame = load_uploaded_frame(self.upload_dir, dataset.file_name)
            return dataset, frame.head(limit) if limit else frame
        if dataset.table_name:
            schema = quote_identifier(dataset.table_schema or "public")
            table = quote_identifier(dataset.table_name)
            sql = f"SELECT * FROM {schema}.{table}"
            if limit:
                sql = f"{sql} LIMIT {limit}"
            return dataset, pd.DataFrame(run_readonly_query(sql))
        return dataset, None

    async def _dataset(self, dataset_id: int) -> Dataset | None:
        return await self.session.get(Dataset, dataset_id)

    def _records(self, frame: pd.DataFrame) -> list[dict[str, Any]]:
        return frame.where(pd.notnull(frame), None).to_dict(orient="records")
