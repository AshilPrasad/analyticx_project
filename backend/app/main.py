"""
main.py — FastAPI app factory. Wires everything together.

All routes are defined in routes.py.
All RAG logic lives in the rag/ folder.
"""

import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import settings
from app.chat_routes import chat_router
from app.database import ensure_db_connected, get_db_status, init_db, purge_expired_sessions
from app.routes import document_router, qa_router

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
    """Run database setup once when the server starts."""
    # In development we allow API startup without DB so local UI/docs can still load.
    await init_db(raise_on_error=settings.APP_ENV.lower() != "development")
    # Purge once at startup, then on a recurring schedule.
    await purge_expired_sessions()
    purge_task = asyncio.create_task(_purge_loop())
    try:
        yield
    finally:
        purge_task.cancel()


app = FastAPI(
    title="AI Q&A API",
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

# Register routes
app.include_router(document_router)
app.include_router(qa_router)
app.include_router(chat_router)


@app.get("/", tags=["Health"])
async def root():
    return {"message": "AI Q&A API is running", "docs": "/docs"}


@app.get("/health", tags=["Health"])
async def health():
    await ensure_db_connected()
    db = get_db_status()
    return {
        "status": "healthy" if db["connected"] else "degraded",
        "version": "1.0.0",
        "database": db,
    }
