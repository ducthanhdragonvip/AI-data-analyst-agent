from pathlib import Path
from typing import Any

import pandas as pd


def load_uploaded_frame(upload_dir: Path, file_name: str) -> pd.DataFrame:
    path = upload_dir / file_name
    suffix = path.suffix.lower()
    if suffix == ".csv":
        return pd.read_csv(path)
    if suffix in {".xlsx", ".xls"}:
        return pd.read_excel(path)
    raise ValueError("Only CSV and XLSX uploads are supported")


def aggregate_for_chart(frame: pd.DataFrame, profile: dict[str, Any]) -> tuple[pd.DataFrame, str, str]:
    columns = profile.get("columns", {})
    x_column = next(
        (
            name
            for name, meta in columns.items()
            if meta.get("semantic_type") in {"categorical", "datetime"} and name in frame.columns
        ),
        None,
    )
    y_column = next(
        (name for name, meta in columns.items() if meta.get("semantic_type") == "numeric" and name in frame.columns),
        None,
    )
    if not x_column or not y_column:
        raise ValueError("Dataset needs at least one categorical/date column and one numeric column to chart")

    if columns[x_column].get("semantic_type") == "datetime":
        working = frame[[x_column, y_column]].copy()
        working[x_column] = pd.to_datetime(working[x_column], errors="coerce").dt.to_period("M").dt.to_timestamp()
        chart_frame = working.dropna(subset=[x_column]).groupby(x_column, as_index=False)[y_column].sum()
        chart_frame = chart_frame.sort_values(x_column)
    else:
        chart_frame = frame.groupby(x_column, as_index=False)[y_column].sum()
        chart_frame = chart_frame.sort_values(y_column, ascending=False).head(20)
    return chart_frame, x_column, y_column


def summarize_frame(display_name: str, frame: pd.DataFrame) -> str:
    lines = [f"Local uploaded dataset: {display_name}", f"Rows: {len(frame)}", f"Columns: {', '.join(frame.columns)}"]
    numeric = frame.select_dtypes(include="number")
    if not numeric.empty:
        lines.append("Numeric summaries:")
        for column in numeric.columns:
            series = numeric[column].dropna()
            if series.empty:
                continue
            lines.append(
                f"- {column}: sum={series.sum():g}, mean={series.mean():g}, min={series.min():g}, max={series.max():g}"
            )
    object_columns = frame.select_dtypes(include=["object", "category", "bool"])
    if not object_columns.empty:
        lines.append("Top values:")
        for column in object_columns.columns[:5]:
            top_values = object_columns[column].value_counts(dropna=True).head(5)
            rendered = ", ".join(f"{index}={value}" for index, value in top_values.items())
            lines.append(f"- {column}: {rendered}")
    return "\n".join(lines)
