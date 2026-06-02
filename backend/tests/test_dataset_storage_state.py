from app.services.dataset_storage_state import dataset_is_imported


def test_dataset_without_table_name_is_not_imported() -> None:
    assert dataset_is_imported(None) is False
    assert dataset_is_imported("") is False


def test_dataset_with_table_name_is_imported() -> None:
    assert dataset_is_imported("uploaded_sales") is True
