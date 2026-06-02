import pytest

from app.services.sql_guard import ensure_readonly_select


@pytest.mark.parametrize(
    "query",
    [
        "select * from sales",
        "WITH monthly AS (SELECT region, sum(revenue) total FROM sales GROUP BY region) SELECT * FROM monthly",
        "  select region, revenue from sales limit 10  ",
    ],
)
def test_readonly_select_queries_are_allowed(query: str) -> None:
    assert ensure_readonly_select(query) == query.strip().rstrip(";")


@pytest.mark.parametrize(
    "query",
    [
        "delete from sales",
        "update sales set revenue = 0",
        "drop table sales",
        "select * from sales; drop table sales;",
        "insert into sales values (1)",
        "copy sales to '/tmp/sales.csv'",
    ],
)
def test_mutating_or_multi_statement_queries_are_rejected(query: str) -> None:
    with pytest.raises(ValueError):
        ensure_readonly_select(query)
