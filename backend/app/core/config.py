"""
core/config.py — Application settings loaded from environment / .env.
"""

from functools import lru_cache

from pydantic import field_validator
from pydantic_settings import BaseSettings


def _normalize_database_url(url: str) -> str:
    """Accept Render's postgresql:// URL and convert for async SQLAlchemy."""
    if url.startswith("postgresql://"):
        return url.replace("postgresql://", "postgresql+asyncpg://", 1)
    if url.startswith("postgres://"):
        return url.replace("postgres://", "postgresql+asyncpg://", 1)
    return url


class Settings(BaseSettings):
    # Database
    DATABASE_URL: str = "postgresql+asyncpg://postgres:Welcome%402026@localhost:5532/chatbot"

    @field_validator("DATABASE_URL", mode="before")
    @classmethod
    def normalize_database_url(cls, v: str) -> str:
        return _normalize_database_url(v)

    # Google Gemini (LLM + embeddings — single provider for the whole RAG stack)
    GOOGLE_API_KEY: str = ""
    LLM_MODEL: str = "gemini-2.5-flash-lite"
    EMBEDDING_MODEL: str = "models/gemini-embedding-001"
    EMBEDDING_DIM: int = 768  # gemini-embedding-001 supports 768 / 1536 / 3072

    # App
    APP_ENV: str = "development"
    CORS_ORIGINS: str = "http://localhost:5173,http://localhost:3000"

    # Chat history retention — sessions older than this are auto-deleted
    CHAT_RETENTION_DAYS: int = 90

    # Authentication (JWT)
    JWT_SECRET: str = "change-me-in-production-please-use-a-long-random-secret"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days

    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",")]

    @property
    def sync_database_url(self) -> str:
        """Sync psycopg3 URL for LangChain PGVector (swaps asyncpg driver)."""
        return self.DATABASE_URL.replace("postgresql+asyncpg", "postgresql+psycopg")

    @property
    def plain_database_url(self) -> str:
        """Plain libpq URL for direct psycopg connections."""
        return self.DATABASE_URL.replace("postgresql+asyncpg", "postgresql")

    class Config:
        env_file = ".env"
        extra = "ignore"


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
