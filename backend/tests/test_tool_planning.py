from src.core.models import Dataset
from src.modules.ai.agents.analyst import plan_tool_calls


def test_chart_question_plans_data_and_visualization_tools() -> None:
    dataset = Dataset(
        id=5,
        source_type="upload",
        display_name="house.csv",
        row_count=3,
        profile={
            "columns": {
                "basement": {"semantic_type": "categorical"},
                "rooms": {"semantic_type": "numeric"},
                "price": {"semantic_type": "numeric"},
            }
        },
    )

    calls = plan_tool_calls("draw a chart about house price demand on room", [dataset], "analysis")

    assert [call["name"] for call in calls] == ["load_csv_dataset", "generate_chart"]
    assert calls[0]["arguments"] == {"dataset_id": 5}
    assert calls[1]["arguments"]["dataset_id"] == 5
    assert calls[1]["arguments"]["x"] == "rooms"
    assert calls[1]["arguments"]["y"] == "price"
    assert calls[1]["arguments"]["aggregation"] == "mean"


def test_report_job_plans_report_tool() -> None:
    dataset = Dataset(id=8, source_type="postgres", display_name="orders", row_count=20, profile={})

    calls = plan_tool_calls("Create report", [dataset], "report")

    assert [call["name"] for call in calls] == ["get_dataset_schema", "describe_dataset", "create_markdown_report"]


def test_chart_question_prefers_rooms_over_bedrooms_when_user_asks_for_room() -> None:
    dataset = Dataset(
        id=6,
        source_type="upload",
        display_name="house.csv",
        row_count=3,
        profile={
            "columns": {
                "bedrooms": {"semantic_type": "numeric"},
                "rooms": {"semantic_type": "numeric"},
                "price": {"semantic_type": "numeric"},
            }
        },
    )

    calls = plan_tool_calls("draw house price demand on room", [dataset], "analysis")

    assert calls[1]["name"] == "generate_chart"
    assert calls[1]["arguments"]["x"] == "rooms"
    assert calls[1]["arguments"]["y"] == "price"


def test_chart_question_about_all_rooms_plans_all_room_related_columns() -> None:
    dataset = Dataset(
        id=9,
        source_type="upload",
        display_name="house-price.csv",
        row_count=545,
        profile={
            "columns": {
                "price": {"semantic_type": "numeric"},
                "area": {"semantic_type": "numeric"},
                "bedrooms": {"semantic_type": "numeric"},
                "bathrooms": {"semantic_type": "numeric"},
                "stories": {"semantic_type": "numeric"},
                "guestroom": {"semantic_type": "categorical"},
                "basement": {"semantic_type": "categorical"},
            }
        },
    )

    calls = plan_tool_calls("draw house price demand on all of the room", [dataset], "analysis")

    assert calls[1]["name"] == "generate_chart"
    assert calls[1]["arguments"]["x"] == ["bedrooms", "bathrooms", "guestroom"]
    assert calls[1]["arguments"]["y"] == "price"
    assert calls[1]["arguments"]["aggregation"] == "mean"
