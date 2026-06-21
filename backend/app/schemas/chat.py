"""
schemas/chat.py — Request/response models for chat sessions and messages.
"""

from datetime import datetime

from pydantic import BaseModel, Field


class SessionItem(BaseModel):
    id: int
    title: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class MessageItem(BaseModel):
    id: int
    role: str
    content: str
    created_at: datetime

    class Config:
        from_attributes = True


class SessionDetail(SessionItem):
    messages: list[MessageItem] = []


class ChatAskRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=2000)
    top_k: int = Field(default=5, ge=1, le=20)


class ChatAskResponse(BaseModel):
    session_id: int
    title: str
    message: MessageItem
