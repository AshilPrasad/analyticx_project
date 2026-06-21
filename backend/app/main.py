"""
main.py — FastAPI application factory.

Layered layout:
  core/     — settings + security (hashing, JWT)
  db/       — engine, models, session lifecycle
  schemas/  — pydantic request/response models
  api/      — route modules, aggregated in api/router.py
  rag/      — retrieval-augmented-generation pipeline (Gemini + pgvector)
"""

import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router
from app.core.config import settings
from app.db.session import init_db, purge_expired_sessions

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
logger = logging.getLogger(__name__)

# How often the background task checks for expired chat sessions.
_PURGE_INTERVAL_SECONDS = 12 * 60 * 60  # twice a day


async def _purge_loop():
    """Background task: periodically delete chat sessions past their retention window."""
    while True:
        try:
            await purge_expired_sessions()
        except Exception:
            logger.exception("Chat session purge failed.")
        await asyncio.sleep(_PURGE_INTERVAL_SECONDS)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialise the database and start the retention purge on startup."""
    # In development we allow API startup without DB so local UI/docs can still load.
    await init_db(raise_on_error=settings.APP_ENV.lower() != "development")
    await purge_expired_sessions()
    purge_task = asyncio.create_task(_purge_loop())
    try:
        yield
    finally:
        purge_task.cancel()


app = FastAPI(
    title="analytix API",
    description="RAG-powered Q&A: FastAPI · PostgreSQL/pgvector · Google Gemini (LLM + embeddings)",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)
