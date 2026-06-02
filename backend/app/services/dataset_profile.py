from typing import Any

import pandas as pd


def _json_safe(value: Any) -> Any:
    if pd.isna(value):
        return None
    if hasattr(value, "isoformat"):
        return value.isoformat()
    if hasattr(value, "item"):
        return value.item()
    return value


def _semantic_type(series: pd.Series) -> str:
    if pd.api.types.is_datetime64_any_dtype(series):
        return "datetime"
    if pd.api.types.is_numeric_dtype(series):
        return "numeric"
    if pd.api.types.is_bool_dtype(series):
        return "boolean"
    unique_ratio = series.nunique(dropna=True) / max(len(series), 1)
    if unique_ratio <= 0.8:
        return "categorical"
    return "text"


def profile_dataframe(frame: pd.DataFrame) -> dict[str, Any]:
    columns: dict[str, Any] = {}
    for name in frame.columns:
        series = frame[name]
        semantic_type = _semantic_type(series)
        stats: dict[str, Any] = {
            "null_count": int(series.isna().sum()),
            "unique_count": int(series.nunique(dropna=True)),
        }
        if semantic_type == "numeric":
            stats.update(
                {
                    "min": _json_safe(series.min()),
                    "max": _json_safe(series.max()),
                    "mean": _json_safe(series.mean()),
                }
            )
        elif semantic_type == "datetime":
            stats.update({"min": _json_safe(series.min()), "max": _json_safe(series.max())})

        samples = [_json_safe(value) for value in series.dropna().head(5).tolist()]
        columns[str(name)] = {
            "dtype": str(series.dtype),
            "semantic_type": semantic_type,
            "stats": stats,
            "samples": samples,
        }

    sample_rows = [
        {str(key): _json_safe(value) for key, value in row.items()}
        for row in frame.head(10).to_dict(orient="records")
    ]
    return {"row_count": int(len(frame)), "columns": columns, "sample_rows": sample_rows}


def profile_to_text(display_name: str, table_schema: str, table_name: str, profile: dict[str, Any]) -> str:
    lines = [
        f"Dataset: {display_name}",
        f"Table: {table_schema}.{table_name}",
        f"Rows: {profile.get('row_count', 0)}",
        "Columns:",
    ]
    for name, meta in profile.get("columns", {}).items():
        stats = meta.get("stats", {})
        sample_text = ", ".join(str(value) for value in meta.get("samples", [])[:3])
        lines.append(
            f"- {name}: {meta.get('semantic_type')} ({meta.get('dtype')}); "
            f"unique={stats.get('unique_count')}; nulls={stats.get('null_count')}; samples={sample_text}"
        )
    return "\n".join(lines)
