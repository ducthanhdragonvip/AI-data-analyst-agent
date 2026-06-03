from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parents[2]
REPO_DIR = BACKEND_DIR.parent


class Settings(BaseSettings):
    database_url: str = "postgresql+asyncpg://analyst:analyst@localhost:5432/analyst"
    sync_database_url: str = "postgresql+psycopg://analyst:analyst@localhost:5432/analyst"
    openai_api_key: str = ""
    openai_model: str = "gpt-4.1-mini"
    embedding_model: str = "text-embedding-3-small"
    storage_dir: Path = BACKEND_DIR / "storage"
    upload_dir: Path = BACKEND_DIR / "storage" / "uploads"
    artifact_dir: Path = BACKEND_DIR / "storage" / "artifacts"
    chroma_path: Path = BACKEND_DIR / "storage" / "chroma"
    cors_origins: list[str] = Field(default_factory=lambda: ["http://localhost:5173"])

    model_config = SettingsConfigDict(env_file=REPO_DIR / ".env", env_file_encoding="utf-8", extra="ignore")

    def ensure_storage(self) -> None:
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.upload_dir.mkdir(parents=True, exist_ok=True)
        self.artifact_dir.mkdir(parents=True, exist_ok=True)
        self.chroma_path.mkdir(parents=True, exist_ok=True)


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    settings.ensure_storage()
    return settings
