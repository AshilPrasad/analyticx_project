"""
llm.py — LangChain ChatGroq: Llama 3 via Groq API (free tier).

Model: llama3-8b-8192
  - Open-source Meta Llama 3, hosted on Groq's fast inference hardware
  - Free tier: 14,400 requests/day, no credit card required
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
        model="llama3-8b-8192",
        groq_api_key=settings.GROQ_API_KEY,
        temperature=0.2,
        max_tokens=1024,
    )
