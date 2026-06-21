"""
vectorstore.py — LangChain PGVector: stores and searches document embeddings.

What it does in plain English:
  - Manages a PostgreSQL table of document chunks + their vector embeddings
  - Uses langchain-postgres (PGVector) to handle storage automatically
  - Provides add, search, and delete operations for document chunks

Tables created automatically by LangChain:
  langchain_pg_collection — one row per named collection
  langchain_pg_embedding  — one row per document chunk (text + vector)
"""

import asyncio
import logging
import psycopg

from functools import lru_cache
from langchain_postgres import PGVector
from langchain_core.documents import Document

from app.config import settings
from app.rag.embeddings import get_embeddings

logger = logging.getLogger(__name__)

COLLECTION_NAME = "rag_documents"


@lru_cache(maxsize=1)
def get_vectorstore() -> PGVector:
    """
    Return a cached PGVector instance connected to PostgreSQL.
    LangChain creates its own tables on first use automatically.
    """
    return PGVector(
        embeddings=get_embeddings(),
        collection_name=COLLECTION_NAME,
        connection=settings.sync_database_url,
    )


async def add_documents(docs: list[Document]) -> list[str]:
    """Add document chunks to the vector store (runs sync in thread pool)."""
    store = get_vectorstore()
    ids = await asyncio.to_thread(store.add_documents, docs)
    logger.info(f"Added {len(ids)} chunks to vectorstore.")
    return ids


async def search_with_scores(query: str, top_k: int = 5) -> list[tuple[Document, float]]:
    """
    Find top-K chunks most similar to the query.
    Returns list of (Document, similarity_score) — higher score = more relevant.
    """
    store = get_vectorstore()
    return await asyncio.to_thread(store.similarity_search_with_relevance_scores, query, k=top_k)


async def delete_by_source(document_name: str) -> int:
    """
    Delete all chunks for a document from LangChain's pgvector table.
    Uses direct psycopg SQL since LangChain has no built-in delete-by-metadata.

    Returns number of deleted rows.
    """
    conn_str = settings.plain_database_url
    query = """
        DELETE FROM langchain_pg_embedding
        WHERE collection_id = (
            SELECT uuid FROM langchain_pg_collection WHERE name = %s
        )
        AND cmetadata->>'source' = %s
    """
    def _delete():
        with psycopg.connect(conn_str) as conn:
            with conn.cursor() as cur:
                try:
                    cur.execute(query, (COLLECTION_NAME, document_name))
                    conn.commit()
                    return cur.rowcount
                except psycopg.errors.UndefinedTable:
                    # LangChain's tables don't exist yet (no document ever ingested).
                    conn.rollback()
                    return 0

    count = await asyncio.to_thread(_delete)
    logger.info(f"Deleted {count} chunks for '{document_name}' from vectorstore.")
    return count
