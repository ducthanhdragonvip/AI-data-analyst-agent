from sqlalchemy import create_engine, text

from src.core.config import get_settings
from src.modules.utils.sql_guard import ensure_readonly_select


def run_readonly_query(query: str) -> list[dict]:
    sql = ensure_readonly_select(query)
    engine = create_engine(get_settings().sync_database_url, pool_pre_ping=True)
    with engine.connect() as conn:
        result = conn.execute(text(sql))
        return [dict(row._mapping) for row in result]
