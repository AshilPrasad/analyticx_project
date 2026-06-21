"""
schemas/config.py — Request/response models for runtime configuration.
"""

from pydantic import BaseModel, Field


class GeminiKeyRequest(BaseModel):
    api_key: str = Field(..., min_length=10, max_length=400)


class ConfigStatus(BaseModel):
    gemini_configured: bool
    llm_model: str
    embedding_model: str
