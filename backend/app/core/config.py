from typing import Annotated

from functools import lru_cache
from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

OPENAI_EMBEDDING_DIMENSIONS = {
    "text-embedding-3-small": 1536,
    "text-embedding-3-large": 3072,
}


class Settings(BaseSettings):
    app_name: str = "Enterprise Copilot API"
    app_env: str = "local"
    app_version: str = "0.1.0"
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    postgres_db: str = "enterprise_copilot"
    postgres_user: str = "postgres"
    postgres_password: str = "postgres"
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    database_url: str | None = None
    embedding_provider: str = "openai"
    embedding_model: str = "text-embedding-3-small"
    embedding_dimensions: int | None = None
    llm_provider: str = "openai"
    llm_model: str = "gpt-5.4-mini"
    openai_api_key: str | None = None
    openai_base_url: str | None = None
    local_storage_root: str = "data/uploads"
    chunk_size: int = 800
    chunk_overlap: int = 150
    chunk_min_length: int = 120
    answer_min_score: float = 0.2
    answer_max_citations: int = 2
    backend_cors_origins: Annotated[list[str], NoDecode] = Field(
        default_factory=lambda: [
            "http://localhost:3000",
            "http://127.0.0.1:3000",
        ]
    )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    @field_validator("backend_cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, value: str | list[str]) -> list[str]:
        if isinstance(value, list):
            return value
        if isinstance(value, str):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return []

    @property
    def resolved_database_url(self) -> str:
        if self.database_url:
            if self.database_url.startswith("postgresql://"):
                return self.database_url.replace(
                    "postgresql://",
                    "postgresql+psycopg://",
                    1,
                )
            return self.database_url
        return (
            f"postgresql://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        ).replace("postgresql://", "postgresql+psycopg://", 1)

    @property
    def resolved_embedding_dimensions(self) -> int:
        if self.embedding_dimensions is not None:
            return self.embedding_dimensions
        if self.embedding_provider == "openai":
            return OPENAI_EMBEDDING_DIMENSIONS.get(self.embedding_model, 1536)
        return 8

    @property
    def resolved_storage_root(self) -> Path:
        return Path(self.local_storage_root).expanduser().resolve()


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
