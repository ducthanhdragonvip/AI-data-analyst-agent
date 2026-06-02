import pandas as pd

from app.services.dataframe_analysis import aggregate_for_chart, summarize_frame


def test_aggregate_for_chart_groups_categorical_by_numeric_sum() -> None:
    frame = pd.DataFrame({"region": ["West", "West", "East"], "revenue": [100, 50, 75]})
    profile = {
        "columns": {
            "region": {"semantic_type": "categorical"},
            "revenue": {"semantic_type": "numeric"},
        }
    }

    chart_frame, x_column, y_column = aggregate_for_chart(frame, profile)

    assert x_column == "region"
    assert y_column == "revenue"
    assert chart_frame.to_dict(orient="records") == [
        {"region": "West", "revenue": 150},
        {"region": "East", "revenue": 75},
    ]


def test_summarize_frame_includes_numeric_totals_and_column_names() -> None:
    frame = pd.DataFrame({"region": ["West", "East"], "revenue": [100, 75]})

    summary = summarize_frame("sales.csv", frame)

    assert "sales.csv" in summary
    assert "Rows: 2" in summary
    assert "revenue: sum=175" in summary
