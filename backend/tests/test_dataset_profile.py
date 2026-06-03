import pandas as pd

from src.modules.data.loaders.dataset_profile import profile_dataframe, profile_to_text


def test_profile_dataframe_describes_rows_columns_and_stats() -> None:
    frame = pd.DataFrame(
        {
            "region": ["east", "west", "east"],
            "amount": [10, 20, 30],
            "sold_at": ["2026-01-01", "2026-02-01", "not-a-date"],
        }
    )

    profile = profile_dataframe(frame)

    assert profile["row_count"] == 3
    assert profile["columns"]["amount"]["semantic_type"] == "numeric"
    assert profile["columns"]["amount"]["stats"]["sum"] == 60
    assert profile["columns"]["region"]["top_values"]["east"] == 2
    assert "sold_at" in profile["columns"]


def test_profile_to_text_includes_table_and_columns() -> None:
    profile = {
        "row_count": 2,
        "columns": {
            "region": {"dtype": "object", "semantic_type": "categorical"},
            "amount": {"dtype": "int64", "semantic_type": "numeric"},
        },
    }

    text = profile_to_text("Sales", "public", "sales", profile)

    assert "Dataset: Sales" in text
    assert "Table: public.sales" in text
    assert "region" in text
    assert "amount" in text
