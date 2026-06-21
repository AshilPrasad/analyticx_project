"""
api/routes/config.py — Runtime configuration endpoints.

Lets the user set their Google Gemini API key from the UI instead of editing
the .env file. The key is validated with a tiny embedding call, applied at
runtime (rebuilding the cached LLM / embeddings / vectorstore clients), and
persisted back to backend/.env so it survives restarts.
"""

import asyncio
import logging
from pathlib import Path

from fastapi import APIRouter, HTTPException

from app.core.config import settings
from app.rag.embeddings import get_embeddings
from app.rag.llm import get_llm
from app.rag.vectorstore import get_vectorstore
from app.schemas.config import ConfigStatus, GeminiKeyRequest

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/config", tags=["Config"])

# backend/.env — three levels up: routes/ -> api/ -> app/ -> backend/
ENV_PATH = Path(__file__).resolve().parents[3] / ".env"


def _clear_caches() -> None:
    """Drop cached clients so they rebuild with the new key."""
    get_embeddings.cache_clear()
    get_llm.cache_clear()
    get_vectorstore.cache_clear()


def _persist_env(key: str) -> None:
    """Upsert GOOGLE_API_KEY in backend/.env (best-effort)."""
    try:
        lines, found = [], False
        if ENV_PATH.exists():
            for line in ENV_PATH.read_text(encoding="utf-8").splitlines():
                if line.startswith("GOOGLE_API_KEY="):
                    lines.append(f"GOOGLE_API_KEY={key}")
                    found = True
                else:
                    lines.append(line)
        if not found:
            lines.append(f"GOOGLE_API_KEY={key}")
        ENV_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")
    except Exception:
        logger.warning("Could not persist GOOGLE_API_KEY to .env (runtime value still applied).")


@router.get("/", response_model=ConfigStatus)
async def get_config():
    """Report whether the Gemini key is configured (never returns the key itself)."""
    return ConfigStatus(
        gemini_configured=bool(settings.GOOGLE_API_KEY),
        llm_model=settings.LLM_MODEL,
        embedding_model=settings.EMBEDDING_MODEL,
    )


@router.post("/gemini-key", response_model=ConfigStatus)
async def set_gemini_key(req: GeminiKeyRequest):
    """Validate and apply a Gemini API key at runtime, then persist it."""
    key = req.api_key.strip()
    previous = settings.GOOGLE_API_KEY

    # Apply the candidate key and rebuild clients
    settings.GOOGLE_API_KEY = key
    _clear_caches()

    # Validate with a lightweight embedding call
    try:
        embeddings = get_embeddings()
        await asyncio.to_thread(embeddings.embed_query, "ping")
    except Exception as exc:
        # Revert on failure
        settings.GOOGLE_API_KEY = previous
        _clear_caches()
        detail = str(exc)
        raise HTTPException(
            status_code=400,
            detail=f"Invalid Gemini API key: {detail[:200]}",
        )

    _persist_env(key)
    logger.info("Gemini API key updated via API.")
    return ConfigStatus(
        gemini_configured=True,
        llm_model=settings.LLM_MODEL,
        embedding_model=settings.EMBEDDING_MODEL,
    )
