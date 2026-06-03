import pytest

from src.modules.data.loaders.datasets import DatasetService, sanitize_table_name


class FakeSession:
    def __init__(self) -> None:
        self.added = []
        self.flushed = False

    def add(self, value) -> None:
        self.added.append(value)
        value.id = len(self.added)

    async def flush(self) -> None:
        self.flushed = True


class ForbiddenBusinessStore:
    def __init__(self) -> None:
        self.called = False

    def upsert_document(self, *args, **kwargs) -> None:
        self.called = True
        raise AssertionError("Datasets must not be written to Chroma")


def test_sanitize_table_name_generates_safe_upload_name() -> None:
    assert sanitize_table_name("2026 Sales Report.csv") == "uploaded_dataset_2026_sales_report"
    assert sanitize_table_name("Revenue!!.csv") == "uploaded_revenue"


@pytest.mark.asyncio
async def test_csv_upload_creates_staged_dataset_without_importing(tmp_path) -> None:
    session = FakeSession()
    business_store = ForbiddenBusinessStore()
    service = DatasetService(session=session, upload_dir=tmp_path, business_store=business_store)

    dataset = await service.ingest_upload("sales.csv", b"region,amount\neast,10\nwest,20\n")

    assert dataset.source_type == "upload"
    assert dataset.display_name == "sales.csv"
    assert dataset.file_name == "sales.csv"
    assert dataset.table_name is None
    assert dataset.is_imported is False
    assert dataset.row_count == 2
    assert (tmp_path / "sales.csv").exists()
    assert business_store.called is False
