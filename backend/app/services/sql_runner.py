from typing import Any

from sqlalchemy import create_engine, text

from app.config import get_settings
from app.services.sql_guard import ensure_readonly_select


def run_readonly_query(query: str, limit: int | None = None) -> list[dict[str, Any]]:
    settings = get_settings()
    safe_query = ensure_readonly_select(query)
    max_rows = limit or settings.max_result_rows
    wrapped = f"SELECT * FROM ({safe_query}) AS analyst_query LIMIT :limit"
    engine = create_engine(settings.sync_database_url, pool_pre_ping=True)
    with engine.connect() as conn:
        conn = conn.execution_options(isolation_level="AUTOCOMMIT")
        conn.execute(text("SET statement_timeout = '15s'"))
        result = conn.execute(text(wrapped), {"limit": max_rows})
        return [dict(row) for row in result.mappings()]
