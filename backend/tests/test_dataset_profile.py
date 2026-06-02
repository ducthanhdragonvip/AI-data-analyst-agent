import pandas as pd

from app.services.dataset_profile import profile_dataframe


def test_profile_dataframe_captures_columns_types_stats_and_samples() -> None:
    frame = pd.DataFrame(
        {
            "region": ["West", "East", "West"],
            "revenue": [100.0, 80.0, 120.0],
            "order_date": pd.to_datetime(["2026-01-01", "2026-01-02", "2026-02-01"]),
        }
    )

    profile = profile_dataframe(frame)

    assert profile["row_count"] == 3
    assert profile["columns"]["region"]["semantic_type"] == "categorical"
    assert profile["columns"]["revenue"]["semantic_type"] == "numeric"
    assert profile["columns"]["revenue"]["stats"]["mean"] == 100.0
    assert profile["columns"]["order_date"]["semantic_type"] == "datetime"
    assert profile["sample_rows"][0]["region"] == "West"
