"""
db/session.py — Async engine, session factory, connection lifecycle, and the
chat-session retention purge.
"""

import logging
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException
from sqlalchemy import delete, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings
from app.db.base import Base
from app.db.models import ChatSession  # noqa: F401 — also registers all models on Base

logger = logging.getLogger(__name__)

engine = create_async_engine(
    settings.DATABASE_URL,
    echo=False,
    pool_pre_ping=True,   # transparently recover from DB restarts / dropped connections
)
AsyncSessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

_db_connected = False
_db_error_message = "Database has not been initialised yet."


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
    """Enable pgvector extension and create application tables on startup."""
    global _db_connected, _db_error_message

    try:
        async with engine.begin() as conn:
            await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
            await conn.run_sync(Base.metadata.create_all)
            # Idempotent migrations for pre-existing tables (added when auth was introduced)
            await conn.execute(text(
                "ALTER TABLE chat_sessions ADD COLUMN IF NOT EXISTS user_id INTEGER"
            ))
            await conn.execute(text(
                "ALTER TABLE ingested_documents ADD COLUMN IF NOT EXISTS user_id INTEGER"
            ))
            await conn.execute(text(
                "ALTER TABLE ingested_documents DROP CONSTRAINT IF EXISTS ingested_documents_document_name_key"
            ))
        _db_connected = True
        _db_error_message = "connected"
        logger.info("Database initialised.")
    except Exception as exc:
        _db_connected = False
        _db_error_message = f"{exc.__class__.__name__}: {exc}"
        logger.warning("Database initialisation failed: %s", _db_error_message)
        if raise_on_error:
            raise


async def purge_expired_sessions() -> int:
    """Delete chat sessions older than the configured retention window.

    Returns the number of sessions deleted. Messages are removed via cascade.
    """
    if not await ensure_db_connected():
        return 0

    cutoff = datetime.now(timezone.utc) - timedelta(days=settings.CHAT_RETENTION_DAYS)
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            delete(ChatSession).where(ChatSession.created_at < cutoff)
        )
        await session.commit()
        deleted = result.rowcount or 0

    if deleted:
        logger.info("Purged %d chat session(s) older than %d days.", deleted, settings.CHAT_RETENTION_DAYS)
    return deleted
