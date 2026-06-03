import pytest

from src.modules.utils.sql_guard import ensure_readonly_select


def test_allows_single_select_query() -> None:
    assert ensure_readonly_select(" SELECT * FROM sales LIMIT 5; ") == "SELECT * FROM sales LIMIT 5"


@pytest.mark.parametrize(
    "query",
    [
        "SELECT * FROM sales; SELECT * FROM users",
        "DELETE FROM sales",
        "CREATE TABLE x(id int)",
        "COPY sales TO STDOUT",
        "UPDATE sales SET amount = 0",
        "VACUUM",
    ],
)
def test_rejects_unsafe_sql(query: str) -> None:
    with pytest.raises(ValueError):
        ensure_readonly_select(query)
