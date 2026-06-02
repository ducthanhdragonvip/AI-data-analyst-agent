from typing import Any

from sqlalchemy import create_engine, text

from app.config import get_settings


TABLE_LIST_SQL = """
SELECT table_schema, table_name
FROM information_schema.tables
WHERE table_schema NOT IN ('pg_catalog', 'information_schema')
ORDER BY table_schema, table_name
"""


def list_database_tables() -> list[dict[str, Any]]:
    settings = get_settings()
    engine = create_engine(settings.sync_database_url, pool_pre_ping=True)
    with engine.connect() as conn:
        result = conn.execute(text(TABLE_LIST_SQL))
        return [dict(row) for row in result.mappings()]


def format_table_rows(rows: list[dict[str, Any]]) -> str:
    if not rows:
        return "No user tables found."
    return "\n".join(f"{row['table_schema']}.{row['table_name']}" for row in rows)


def list_database_tables_text() -> str:
    return format_table_rows(list_database_tables())
