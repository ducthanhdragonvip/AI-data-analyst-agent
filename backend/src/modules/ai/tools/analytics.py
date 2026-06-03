from pathlib import Path
from typing import Any

import pandas as pd
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.ai.tools.data_access import DataAccessTools
from src.modules.ai.tools.result import tool_result


class AnalyticsTools:
    def __init__(self, session: AsyncSession, upload_dir: Path | None = None) -> None:
        self.data_access = DataAccessTools(session, upload_dir=upload_dir)

    async def describe_dataset(self, dataset_id: int) -> dict[str, Any]:
        dataset, frame = await self.data_access.frame_for_dataset(dataset_id, limit=1000)
        if not dataset or frame is None:
            return tool_result("describe_dataset", "error", "Dataset not found or not readable")
        numeric = frame.select_dtypes(include="number")
        stats = {
            column: {
                "sum": float(series.sum()),
                "mean": float(series.mean()),
                "min": float(series.min()),
                "max": float(series.max()),
            }
            for column, series in numeric.items()
            if not series.dropna().empty
        }
        return tool_result(
            "describe_dataset",
            "ok",
            f"Described {dataset.display_name}.",
            {"row_count": len(frame), "columns": list(frame.columns), "numeric_stats": stats},
        )

    async def aggregate_dataset(
        self,
        dataset_id: int,
        group_by: str,
        metric: str,
        operation: str = "sum",
    ) -> dict[str, Any]:
        dataset, frame = await self.data_access.frame_for_dataset(dataset_id)
        if not dataset or frame is None:
            return tool_result("aggregate_dataset", "error", "Dataset not found or not readable")
        if group_by not in frame.columns or metric not in frame.columns:
            return tool_result("aggregate_dataset", "error", "Requested columns are not in the dataset")
        if operation not in {"sum", "mean", "count", "min", "max"}:
            return tool_result("aggregate_dataset", "error", "Unsupported aggregation operation")
        grouped = getattr(frame.groupby(group_by, as_index=False)[metric], operation)()
        grouped = grouped.sort_values(metric, ascending=False).head(100)
        return tool_result(
            "aggregate_dataset",
            "ok",
            f"Aggregated {metric} by {group_by} using {operation}.",
            {"rows": self._records(grouped), "group_by": group_by, "metric": metric, "operation": operation},
        )

    async def correlate_dataset(self, dataset_id: int, columns: list[str] | None = None) -> dict[str, Any]:
        dataset, frame = await self.data_access.frame_for_dataset(dataset_id, limit=5000)
        if not dataset or frame is None:
            return tool_result("correlate_dataset", "error", "Dataset not found or not readable")
        selected = columns or list(frame.select_dtypes(include="number").columns)
        missing = [column for column in selected if column not in frame.columns]
        if missing:
            return tool_result("correlate_dataset", "error", f"Column not found: {missing[0]}")
        numeric = frame[selected].select_dtypes(include="number")
        if numeric.shape[1] < 2:
            return tool_result("correlate_dataset", "error", "At least two numeric columns are required")
        return tool_result(
            "correlate_dataset",
            "ok",
            f"Computed correlations for {dataset.display_name}.",
            {"correlation": numeric.corr().round(4).to_dict()},
        )

    async def detect_basic_anomalies(self, dataset_id: int, column: str) -> dict[str, Any]:
        dataset, frame = await self.data_access.frame_for_dataset(dataset_id, limit=5000)
        if not dataset or frame is None:
            return tool_result("detect_basic_anomalies", "error", "Dataset not found or not readable")
        if column not in frame.columns:
            return tool_result("detect_basic_anomalies", "error", "Column not found")
        series = pd.to_numeric(frame[column], errors="coerce").dropna()
        if series.empty:
            return tool_result("detect_basic_anomalies", "error", "Column is not numeric")
        mean = series.mean()
        std = series.std()
        if not std:
            anomalies = frame.iloc[[]]
        else:
            anomalies = frame.loc[(pd.to_numeric(frame[column], errors="coerce") - mean).abs() > (3 * std)]
        return tool_result(
            "detect_basic_anomalies",
            "ok",
            f"Detected {len(anomalies)} basic anomalies in {column}.",
            {"rows": self._records(anomalies.head(100)), "column": column, "threshold": "abs(z_score) > 3"},
        )

    def _records(self, frame: pd.DataFrame) -> list[dict[str, Any]]:
        return frame.where(pd.notnull(frame), None).to_dict(orient="records")
