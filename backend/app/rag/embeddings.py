"""
embeddings.py — Converts text into vector numbers using Google Gemini.

Model: models/gemini-embedding-001 (configurable via EMBEDDING_MODEL)
  - Hosted by Google Gemini (free tier, requires GOOGLE_API_KEY)
  - Output dimensionality configurable via EMBEDDING_DIM (768 / 1536 / 3072)
  - No heavy local ML dependencies (no PyTorch)
"""

from functools import lru_cache
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from app.core.config import settings


@lru_cache(maxsize=1)
def get_embeddings() -> GoogleGenerativeAIEmbeddings:
    """Return a cached Google Gemini embeddings instance."""
    if not settings.GOOGLE_API_KEY:
        raise ValueError(
            "GOOGLE_API_KEY is not set. Get a free key at https://aistudio.google.com/app/apikey"
        )
    return GoogleGenerativeAIEmbeddings(
        model=settings.EMBEDDING_MODEL,
        google_api_key=settings.GOOGLE_API_KEY,
        output_dimensionality=settings.EMBEDDING_DIM,
    )
