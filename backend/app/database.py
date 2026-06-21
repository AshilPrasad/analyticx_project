"""
database.py — Async DB connection + lightweight metadata table.

LangChain PGVector manages its own tables (langchain_pg_collection,
langchain_pg_embedding). This file only tracks which documents have
been ingested so we can list and delete them via the API.
"""

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import Column, Integer, String, DateTime, text
from sqlalchemy.sql import func
from app.config import settings
from fastapi import HTTPException
import logging

logger = logging.getLogger(__name__)

engine = create_async_engine(settings.DATABASE_URL, echo=False)
AsyncSessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
_db_connected = False
_db_error_message = "Database has not been initialised yet."


class Base(DeclarativeBase):
    pass


class IngestedDocument(Base):
    """Tracks documents uploaded to the knowledge base (metadata only, no embeddings)."""
    __tablename__ = "ingested_documents"

    id            = Column(Integer, primary_key=True)
    document_name = Column(String(512), nullable=False, unique=True)
    chunk_count   = Column(Integer, nullable=False, default=0)
    created_at    = Column(DateTime(timezone=True), server_default=func.now())


async def ensure_db_connected() -> bool:
    """Retry DB initialisation if the database was offline at startup."""
    if _db_connected:
        return True
    await init_db(raise_on_error=False)
    return _db_connected


async def get_db():
    """FastAPI dependency — yields an async DB session."""
    if not await ensure_db_connected():
        raise HTTPException(
            status_code=503,
            detail="Database is not connected. Start PostgreSQL on port 5532 and try again.",
        )

    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise


def get_db_status() -> dict[str, str | bool]:
    """Expose database connectivity status for health checks."""
    return {
        "connected": _db_connected,
        "message": "connected" if _db_connected else _db_error_message,
    }


async def init_db(*, raise_on_error: bool = True):
    """Enable pgvector extension and create metadata tables on startup."""
    global _db_connected, _db_error_message

    try:
        async with engine.begin() as conn:
            await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
            await conn.run_sync(Base.metadata.create_all)
        _db_connected = True
        _db_error_message = "connected"
        logger.info("Database initialised.")
    except Exception as exc:
        _db_connected = False
        _db_error_message = f"{exc.__class__.__name__}: {exc}"
        logger.warning("Database initialisation failed: %s", _db_error_message)
        if raise_on_error:
            raise
