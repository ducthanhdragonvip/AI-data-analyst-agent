from pathlib import Path

import pandas as pd


def read_tabular_file(path: Path) -> pd.DataFrame:
    suffix = path.suffix.lower()
    if suffix == ".csv":
        return pd.read_csv(path)
    raise ValueError("Only CSV uploads are supported")


def load_uploaded_frame(upload_dir: Path, file_name: str) -> pd.DataFrame:
    return read_tabular_file(upload_dir / file_name)


def summarize_frame(display_name: str, frame: pd.DataFrame) -> str:
    lines = [f"Local uploaded dataset: {display_name}", f"Rows: {len(frame)}", f"Columns: {', '.join(frame.columns)}"]
    numeric = frame.select_dtypes(include="number")
    for column in numeric.columns:
        series = numeric[column].dropna()
        if not series.empty:
            lines.append(
                f"- {column}: sum={series.sum():g}, mean={series.mean():g}, min={series.min():g}, max={series.max():g}"
            )
    return "\n".join(lines)


def aggregate_for_chart(frame: pd.DataFrame, profile: dict) -> tuple[pd.DataFrame, str, str]:
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
        raise ValueError("Dataset needs one categorical/date column and one numeric column to chart")
    chart_frame = frame.groupby(x_column, as_index=False)[y_column].sum().sort_values(y_column, ascending=False).head(20)
    return chart_frame, x_column, y_column
