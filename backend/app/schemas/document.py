"""
schemas/document.py — Request/response models for documents and Q&A.
"""

from pydantic import BaseModel, Field

from app.core.config import settings


class IngestResponse(BaseModel):
    message: str
    document_name: str
    chunks_created: int


class DocumentItem(BaseModel):
    document_name: str
    chunk_count: int


class QARequest(BaseModel):
    question: str = Field(..., min_length=3, max_length=2000, description="Your question")
    top_k: int = Field(default=5, ge=1, le=20, description="Number of chunks to retrieve")


class SourceChunk(BaseModel):
    document_name: str
    content: str
    similarity: float


class QAResponse(BaseModel):
    question: str
    answer: str
    sources: list[SourceChunk]
    model: str = settings.LLM_MODEL
