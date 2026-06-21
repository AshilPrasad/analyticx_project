"""
embeddings.py — Converts text into vector numbers using LangChain + HuggingFace.

Model: sentence-transformers/all-MiniLM-L6-v2
  - Runs 100% locally (no internet after first download, no API key)
  - Produces 384-dimensional embeddings
  - Loaded once at startup and cached in memory
"""

from functools import lru_cache
from langchain_huggingface import HuggingFaceEmbeddings


@lru_cache(maxsize=1)
def get_embeddings() -> HuggingFaceEmbeddings:
    """Return a cached HuggingFace embeddings instance."""
    return HuggingFaceEmbeddings(
        model_name="sentence-transformers/all-MiniLM-L6-v2",
        model_kwargs={"device": "cpu"},
        encode_kwargs={"normalize_embeddings": True},
    )
