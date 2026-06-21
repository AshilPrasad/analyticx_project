"""
llm.py — LangChain ChatGroq: LLM via Groq API (free tier).

Model: configurable via LLM_MODEL (default: openai/gpt-oss-20b)
  - Hosted on Groq's fast inference hardware
  - Free tier, no credit card required
  - temperature=0.2: answers are factual, not creative/random
"""

from functools import lru_cache
from langchain_groq import ChatGroq
from app.config import settings


@lru_cache(maxsize=1)
def get_llm() -> ChatGroq:
    """Return a cached ChatGroq LLM instance."""
    if not settings.GROQ_API_KEY:
        raise ValueError(
            "GROQ_API_KEY is not set. Get a free key at https://console.groq.com"
        )
    return ChatGroq(
        model=settings.LLM_MODEL,
        groq_api_key=settings.GROQ_API_KEY,
        temperature=0.2,
        max_tokens=1024,
    )
