from typing import Any

import pandas as pd


def _semantic_type(series: pd.Series) -> str:
    if pd.api.types.is_numeric_dtype(series):
        return "numeric"
    if pd.api.types.is_datetime64_any_dtype(series):
        return "datetime"
    parsed = pd.to_datetime(series, errors="coerce")
    if len(series) and parsed.notna().mean() >= 0.8:
        return "datetime"
    unique_ratio = series.nunique(dropna=True) / max(len(series), 1)
    if unique_ratio <= 0.5 or series.nunique(dropna=True) <= 25:
        return "categorical"
    return "text"


def profile_dataframe(frame: pd.DataFrame) -> dict[str, Any]:
    columns: dict[str, Any] = {}
    for column in frame.columns:
        series = frame[column]
        semantic = _semantic_type(series)
        meta: dict[str, Any] = {
            "dtype": str(series.dtype),
            "semantic_type": semantic,
            "null_count": int(series.isna().sum()),
            "non_null_count": int(series.notna().sum()),
        }
        if semantic == "numeric":
            numeric = pd.to_numeric(series, errors="coerce").dropna()
            if not numeric.empty:
                meta["stats"] = {
                    "sum": float(numeric.sum()),
                    "mean": float(numeric.mean()),
                    "min": float(numeric.min()),
                    "max": float(numeric.max()),
                }
        elif semantic in {"categorical", "text"}:
            meta["top_values"] = {str(k): int(v) for k, v in series.value_counts(dropna=True).head(10).items()}
        columns[str(column)] = meta
    return {"row_count": int(len(frame)), "columns": columns}


def profile_to_text(display_name: str, table_schema: str | None, table_name: str | None, profile: dict[str, Any]) -> str:
    lines = [f"Dataset: {display_name}", f"Rows: {profile.get('row_count', 0)}"]
    if table_schema and table_name:
        lines.append(f"Table: {table_schema}.{table_name}")
    else:
        lines.append("Table: staged upload, not imported")
    for name, meta in profile.get("columns", {}).items():
        lines.append(f"- {name}: {meta.get('dtype')} ({meta.get('semantic_type')})")
    return "\n".join(lines)
