"""
api/routes/health.py — Liveness / readiness endpoints.
"""

from fastapi import APIRouter

from app.db.session import ensure_db_connected, get_db_status

router = APIRouter(tags=["Health"])


@router.get("/")
async def root():
    return {"message": "AI Q&A API is running", "docs": "/docs"}


@router.get("/health")
async def health():
    await ensure_db_connected()
    db = get_db_status()
    return {
        "status": "healthy" if db["connected"] else "degraded",
        "version": "1.0.0",
        "database": db,
    }
