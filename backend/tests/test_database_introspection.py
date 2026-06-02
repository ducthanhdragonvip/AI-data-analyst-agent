from app.services.database_introspection import format_table_rows


def test_format_table_rows_renders_schema_qualified_table_names() -> None:
    rows = [
        {"table_schema": "public", "table_name": "datasets"},
        {"table_schema": "public", "table_name": "uploaded_sales"},
    ]

    assert format_table_rows(rows) == "public.datasets\npublic.uploaded_sales"


def test_format_table_rows_handles_empty_database() -> None:
    assert format_table_rows([]) == "No user tables found."
