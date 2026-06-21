from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # Database
    DATABASE_URL: str = "postgresql+asyncpg://postgres:Welcome%402026@localhost:5433/chatbot"

    # Groq
    GROQ_API_KEY: str = ""

    # App
    APP_ENV: str = "development"
    CORS_ORIGINS: str = "http://localhost:5173,http://localhost:3000"

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
