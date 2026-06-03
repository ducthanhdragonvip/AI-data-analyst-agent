from src.core.config import Settings


def test_settings_normalizes_railway_postgres_url_for_async_and_sync_sqlalchemy() -> None:
    settings = Settings(
        database_url="postgresql://user:pass@host.railway.internal:5432/railway",
        sync_database_url=None,
    )

    assert settings.database_url == "postgresql+asyncpg://user:pass@host.railway.internal:5432/railway"
    assert settings.sync_database_url == "postgresql+psycopg://user:pass@host.railway.internal:5432/railway"
