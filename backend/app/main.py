"""
main.py — FastAPI app factory. Wires everything together.

All routes are defined in routes.py.
All RAG logic lives in the rag/ folder.
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import settings
from app.database import ensure_db_connected, get_db_status, init_db
from app.routes import document_router, qa_router

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Run database setup once when the server starts."""
    # In development we allow API startup without DB so local UI/docs can still load.
    await init_db(raise_on_error=settings.APP_ENV.lower() != "development")
    yield


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
