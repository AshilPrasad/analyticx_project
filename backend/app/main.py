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
from app.database import init_db
from app.routes import document_router, qa_router

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Run database setup once when the server starts."""
    await init_db()
    yield


app = FastAPI(
    title="AI Q&A API",
    description="RAG-powered Q&A: FastAPI · PostgreSQL/pgvector · sentence-transformers · Groq (Llama 3)",
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
    return {"status": "healthy", "version": "1.0.0"}
