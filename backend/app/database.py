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
import logging

logger = logging.getLogger(__name__)

engine = create_async_engine(settings.DATABASE_URL, echo=False)
AsyncSessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


class IngestedDocument(Base):
    """Tracks documents uploaded to the knowledge base (metadata only, no embeddings)."""
    __tablename__ = "ingested_documents"

    id            = Column(Integer, primary_key=True)
    document_name = Column(String(512), nullable=False, unique=True)
    chunk_count   = Column(Integer, nullable=False, default=0)
    created_at    = Column(DateTime(timezone=True), server_default=func.now())


async def get_db():
    """FastAPI dependency — yields an async DB session."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise


async def init_db():
    """Enable pgvector extension and create metadata tables on startup."""
    async with engine.begin() as conn:
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database initialised.")
