"""
database.py — Async DB connection + application tables.

LangChain PGVector manages its own tables (langchain_pg_collection,
langchain_pg_embedding) for embeddings. This file defines:
  - IngestedDocument : tracks uploaded documents (knowledge base)
  - ChatSession      : a ChatGPT-style conversation
  - ChatMessage      : individual user/assistant messages in a session

Chat sessions older than CHAT_RETENTION_DAYS are purged automatically.
"""

import logging

from datetime import datetime, timedelta, timezone

from fastapi import HTTPException
from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    delete,
    text,
)
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, relationship
from sqlalchemy.sql import func

from app.config import settings

logger = logging.getLogger(__name__)

engine = create_async_engine(
    settings.DATABASE_URL,
    echo=False,
    pool_pre_ping=True,   # transparently recover from DB restarts / dropped connections
)
AsyncSessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
_db_connected = False
_db_error_message = "Database has not been initialised yet."


class Base(DeclarativeBase):
    pass


class User(Base):
    """An application user (authentication)."""
    __tablename__ = "users"

    id              = Column(Integer, primary_key=True)
    email           = Column(String(255), nullable=False, unique=True, index=True)
    name            = Column(String(120), nullable=True)
    hashed_password = Column(String(255), nullable=False)
    created_at      = Column(DateTime(timezone=True), server_default=func.now())


class IngestedDocument(Base):
    """Tracks documents uploaded to the knowledge base (metadata only, no embeddings)."""
    __tablename__ = "ingested_documents"

    id            = Column(Integer, primary_key=True)
    user_id       = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True)
    document_name = Column(String(512), nullable=False)
    chunk_count   = Column(Integer, nullable=False, default=0)
    created_at    = Column(DateTime(timezone=True), server_default=func.now())


class ChatSession(Base):
    """A ChatGPT-style conversation thread."""
    __tablename__ = "chat_sessions"

    id         = Column(Integer, primary_key=True)
    user_id    = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True)
    title      = Column(String(255), nullable=False, default="New chat")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    messages = relationship(
        "ChatMessage",
        back_populates="session",
        cascade="all, delete-orphan",
        order_by="ChatMessage.id",
    )


class ChatMessage(Base):
    """A single message (user question or assistant answer) within a session."""
    __tablename__ = "chat_messages"

    id         = Column(Integer, primary_key=True)
    session_id = Column(
        Integer,
        ForeignKey("chat_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    role       = Column(String(16), nullable=False)  # 'user' | 'assistant'
    content    = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    session = relationship("ChatSession", back_populates="messages")


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
