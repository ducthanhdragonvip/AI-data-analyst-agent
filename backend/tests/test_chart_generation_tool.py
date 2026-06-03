import pytest

from src.core.models import Dataset
from src.modules.ai.tools.chart_generation import ChartGenerationTool


class FakeSession:
    def __init__(self) -> None:
        self.added = []

    def add(self, value) -> None:
        self.added.append(value)
        value.id = len(self.added)

    async def flush(self) -> None:
        return None


@pytest.mark.asyncio
async def test_chart_generation_tool_returns_plotly_artifact_payload_for_frontend(tmp_path) -> None:
    upload = tmp_path / "sales.csv"
    upload.write_text("region,amount\neast,10\nwest,20\neast,5\n", encoding="utf-8")
    dataset = Dataset(
        id=1,
        source_type="upload",
        display_name="sales.csv",
        table_schema=None,
        table_name=None,
        file_name="sales.csv",
        row_count=3,
        profile={
            "row_count": 3,
            "columns": {
                "region": {"dtype": "object", "semantic_type": "categorical"},
                "amount": {"dtype": "int64", "semantic_type": "numeric"},
            },
        },
    )

    artifact = await ChartGenerationTool(FakeSession(), upload_dir=tmp_path).run(job_id=42, dataset=dataset)

    assert artifact.kind == "plotly"
    assert artifact.mime_type == "application/json"
    assert artifact.payload["data"][0]["type"] == "bar"
    assert artifact.payload["data"][0]["x"] == ["west", "east"]
    assert artifact.payload["data"][0]["y"] == [20, 15]
    assert artifact.payload["layout"]["title"] == "sales.csv: amount by region"


@pytest.mark.asyncio
async def test_chart_generation_tool_uses_requested_columns_and_mean_aggregation(tmp_path) -> None:
    upload = tmp_path / "houses.csv"
    upload.write_text(
        "basement,rooms,price\nyes,2,200\nno,2,300\nyes,3,600\nno,3,900\n",
        encoding="utf-8",
    )
    dataset = Dataset(
        id=1,
        source_type="upload",
        display_name="houses.csv",
        table_schema=None,
        table_name=None,
        file_name="houses.csv",
        row_count=4,
        profile={
            "row_count": 4,
            "columns": {
                "basement": {"dtype": "object", "semantic_type": "categorical"},
                "rooms": {"dtype": "int64", "semantic_type": "numeric"},
                "price": {"dtype": "int64", "semantic_type": "numeric"},
            },
        },
    )
    session = FakeSession()
    session.dataset = dataset

    async def get(model, object_id):
        return dataset if model is Dataset and object_id == dataset.id else None

    session.get = get

    result = await ChartGenerationTool(session, upload_dir=tmp_path, job_id=42).generate_chart(
        dataset_id=1,
        chart_type="bar",
        x="rooms",
        y="price",
        aggregation="mean",
    )

    assert result["status"] == "ok"
    assert session.added[0].payload["data"][0]["x"] == ["3", "2"]
    assert session.added[0].payload["data"][0]["y"] == [750, 250]
    assert session.added[0].payload["layout"]["title"] == "houses.csv: average price by rooms"


@pytest.mark.asyncio
async def test_chart_generation_tool_supports_multiple_room_columns(tmp_path) -> None:
    upload = tmp_path / "houses.csv"
    upload.write_text(
        "bedrooms,bathrooms,guestroom,price\n2,1,no,200\n2,2,yes,300\n3,2,no,600\n3,3,yes,900\n",
        encoding="utf-8",
    )
    dataset = Dataset(
        id=2,
        source_type="upload",
        display_name="houses.csv",
        table_schema=None,
        table_name=None,
        file_name="houses.csv",
        row_count=4,
        profile={
            "row_count": 4,
            "columns": {
                "bedrooms": {"dtype": "int64", "semantic_type": "numeric"},
                "bathrooms": {"dtype": "int64", "semantic_type": "numeric"},
                "guestroom": {"dtype": "object", "semantic_type": "categorical"},
                "price": {"dtype": "int64", "semantic_type": "numeric"},
            },
        },
    )
    session = FakeSession()

    async def get(model, object_id):
        return dataset if model is Dataset and object_id == dataset.id else None

    session.get = get

    result = await ChartGenerationTool(session, upload_dir=tmp_path, job_id=43).generate_chart(
        dataset_id=2,
        chart_type="bar",
        x=["bedrooms", "bathrooms", "guestroom"],
        y="price",
        aggregation="mean",
    )

    assert result["status"] == "ok"
    assert [trace["name"] for trace in session.added[0].payload["data"]] == ["bedrooms", "bathrooms", "guestroom"]
    assert session.added[0].payload["layout"]["title"] == "houses.csv: average price by room-related fields"
