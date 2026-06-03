from sqlalchemy import create_engine, inspect, text

from src.core.config import get_settings

INTERNAL_TABLES = {"datasets", "conversations", "messages", "jobs", "artifacts"}


def list_user_tables(schema: str = "public") -> list[dict[str, str]]:
    engine = create_engine(get_settings().sync_database_url, pool_pre_ping=True)
    inspector = inspect(engine)
    return [
        {"table_schema": schema, "table_name": table_name}
        for table_name in inspector.get_table_names(schema=schema)
        if table_name not in INTERNAL_TABLES
    ]


def count_rows(schema: str, table_name: str) -> int:
    engine = create_engine(get_settings().sync_database_url, pool_pre_ping=True)
    with engine.connect() as conn:
        return int(conn.execute(text(f"SELECT count(*) FROM {quote_identifier(schema)}.{quote_identifier(table_name)}")).scalar_one())


def quote_identifier(identifier: str) -> str:
    return '"' + identifier.replace('"', '""') + '"'
