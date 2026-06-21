"""
api/router.py — Aggregates all route modules into a single API router.
"""

from fastapi import APIRouter

from app.api.routes import auth, chat, config, documents, health, qa

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(auth.router)
api_router.include_router(documents.router)
api_router.include_router(qa.router)
api_router.include_router(chat.router)
api_router.include_router(config.router)
