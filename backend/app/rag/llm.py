"""
llm.py — LangChain ChatGoogleGenerativeAI: LLM via Google Gemini API (free tier).

Model: configurable via LLM_MODEL (default: gemini-2.5-flash)
  - Hosted by Google Gemini (free tier, requires GOOGLE_API_KEY)
  - Same API key as embeddings — single provider for the whole RAG stack
  - temperature=0.2: answers are factual, not creative/random
"""

from functools import lru_cache
from langchain_google_genai import ChatGoogleGenerativeAI
from app.config import settings


@lru_cache(maxsize=1)
def get_llm() -> ChatGoogleGenerativeAI:
    """Return a cached Google Gemini chat LLM instance."""
    if not settings.GOOGLE_API_KEY:
        raise ValueError(
            "GOOGLE_API_KEY is not set. Get a free key at https://aistudio.google.com/app/apikey"
        )
    return ChatGoogleGenerativeAI(
        model=settings.LLM_MODEL,
        google_api_key=settings.GOOGLE_API_KEY,
        temperature=0.2,
        max_output_tokens=1024,
    )
