import pytest

from src.core.models import Dataset
from src.modules.ai.tools.registry import APPROVED_TOOL_NAMES, ToolRegistry


class FakeSession:
    def __init__(self, dataset=None) -> None:
        self.dataset = dataset
        self.added = []

    async def get(self, model, object_id):
        if model is Dataset and self.dataset and object_id == self.dataset.id:
            return self.dataset
        return None

    def add(self, value) -> None:
        self.added.append(value)
        value.id = len(self.added)

    async def flush(self) -> None:
        return None


def test_tool_registry_exposes_only_approved_backend_tools() -> None:
    registry = ToolRegistry(FakeSession())

    assert registry.tool_names() == APPROVED_TOOL_NAMES
    assert registry.tool_definitions_text().count("load_csv_dataset") == 1


@pytest.mark.asyncio
async def test_data_access_tool_loads_csv_without_prompting_raw_rows_by_default(tmp_path) -> None:
    upload = tmp_path / "sales.csv"
    upload.write_text("region,amount\neast,10\nwest,20\n", encoding="utf-8")
    dataset = Dataset(
        id=7,
        source_type="upload",
        display_name="sales.csv",
        table_schema=None,
        table_name=None,
        file_name="sales.csv",
        row_count=2,
        profile={
            "row_count": 2,
            "columns": {
                "region": {"dtype": "object", "semantic_type": "categorical"},
                "amount": {"dtype": "int64", "semantic_type": "numeric"},
            },
        },
    )
    registry = ToolRegistry(FakeSession(dataset), upload_dir=tmp_path)

    result = await registry.execute("load_csv_dataset", {"dataset_id": 7})

    assert result["status"] == "ok"
    assert result["data"]["row_count"] == 2
    assert result["data"]["columns"] == ["region", "amount"]
    assert "rows" not in result["data"]


@pytest.mark.asyncio
async def test_visualization_tool_returns_plotly_artifact_id_and_payload(tmp_path) -> None:
    upload = tmp_path / "sales.csv"
    upload.write_text("region,amount\neast,10\nwest,20\neast,5\n", encoding="utf-8")
    dataset = Dataset(
        id=3,
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
    session = FakeSession(dataset)
    registry = ToolRegistry(session, job_id=99, upload_dir=tmp_path)

    result = await registry.execute(
        "generate_chart",
        {"dataset_id": 3, "chart_type": "bar", "x": "region", "y": "amount", "aggregation": "sum"},
    )

    assert result["status"] == "ok"
    assert result["artifact_ids"] == [1]
    assert session.added[0].kind == "plotly"
    assert session.added[0].payload["data"][0]["x"] == ["west", "east"]
    assert session.added[0].payload["data"][0]["y"] == [20, 15]


@pytest.mark.asyncio
async def test_reporting_tool_creates_markdown_artifact(tmp_path, monkeypatch) -> None:
    from src.core.config import get_settings

    settings = get_settings()
    monkeypatch.setattr(settings, "artifact_dir", tmp_path)
    session = FakeSession()
    registry = ToolRegistry(session, job_id=12)

    result = await registry.execute(
        "create_markdown_report",
        {"title": "Sales report", "sections": ["# Summary", "Revenue increased"], "artifact_ids": []},
    )

    assert result["status"] == "ok"
    assert result["artifact_ids"] == [1]
    assert session.added[0].kind == "report"
    assert (tmp_path / "job-12-report.md").read_text(encoding="utf-8") == "# Summary\n\nRevenue increased"
