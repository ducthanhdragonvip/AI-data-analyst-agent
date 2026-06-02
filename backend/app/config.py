from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    openai_api_key: str = ""
    openai_model: str = "gpt-4o"
    database_url: str = "postgresql+asyncpg://analyst:analyst@localhost:5432/analyst"
    sync_database_url: str = "postgresql+psycopg://analyst:analyst@localhost:5432/analyst"
    chroma_path: Path = Path("./storage/chroma")
    upload_dir: Path = Path("./storage/uploads")
    artifact_dir: Path = Path("./storage/artifacts")
    backend_cors_origins: str = "http://localhost:5173"
    max_result_rows: int = Field(default=500, ge=1, le=5000)

    model_config = SettingsConfigDict(env_file="../.env", env_file_encoding="utf-8", extra="ignore")

    @property
    def cors_origins(self) -> list[str]:
        return [origin.strip() for origin in self.backend_cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    settings.upload_dir.mkdir(parents=True, exist_ok=True)
    settings.artifact_dir.mkdir(parents=True, exist_ok=True)
    settings.chroma_path.mkdir(parents=True, exist_ok=True)
    return settings
