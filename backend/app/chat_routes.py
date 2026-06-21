"""
chat_routes.py — ChatGPT-style conversation endpoints.

/api/chat/sessions                  — create / list conversations
/api/chat/sessions/{id}             — fetch full conversation / delete it
/api/chat/sessions/{id}/messages    — ask a question (RAG) within a conversation

Chat history is persisted in PostgreSQL and auto-purged after the configured
retention window (see database.purge_expired_sessions).
"""

import logging
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import ChatMessage, ChatSession, get_db
from app.rag.chain import run_rag_chain

logger = logging.getLogger(__name__)

chat_router = APIRouter(prefix="/api/chat", tags=["Chat"])


# ── Schemas ───────────────────────────────────────────────────────────────────

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


# ── Helpers ───────────────────────────────────────────────────────────────────

def _make_title(text: str) -> str:
    """Derive a short conversation title from the first user message."""
    clean = " ".join(text.strip().split())
    return (clean[:48] + "…") if len(clean) > 48 else (clean or "New chat")


async def _get_session_or_404(session_id: int, db: AsyncSession) -> ChatSession:
    session = await db.get(ChatSession, session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Chat session not found.")
    return session


# ── Session routes ────────────────────────────────────────────────────────────

@chat_router.post("/sessions", response_model=SessionItem, status_code=201)
async def create_session(db: AsyncSession = Depends(get_db)):
    """Create a new (empty) conversation."""
    session = ChatSession(title="New chat")
    db.add(session)
    await db.commit()
    await db.refresh(session)
    return session


@chat_router.get("/sessions", response_model=list[SessionItem])
async def list_sessions(db: AsyncSession = Depends(get_db)):
    """List all conversations, most recently updated first."""
    rows = (
        await db.execute(select(ChatSession).order_by(ChatSession.updated_at.desc()))
    ).scalars().all()
    return rows


@chat_router.get("/sessions/{session_id}", response_model=SessionDetail)
async def get_session(session_id: int, db: AsyncSession = Depends(get_db)):
    """Fetch a conversation with all of its messages."""
    result = await db.execute(
        select(ChatSession)
        .where(ChatSession.id == session_id)
        .options(selectinload(ChatSession.messages))
    )
    session = result.scalar_one_or_none()
    if session is None:
        raise HTTPException(status_code=404, detail="Chat session not found.")
    return session


@chat_router.delete("/sessions/{session_id}", status_code=204)
async def delete_session(session_id: int, db: AsyncSession = Depends(get_db)):
    """Delete a conversation and all of its messages."""
    result = await db.execute(delete(ChatSession).where(ChatSession.id == session_id))
    await db.commit()
    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="Chat session not found.")


# ── Message route (RAG) ───────────────────────────────────────────────────────

@chat_router.post("/sessions/{session_id}/messages", response_model=ChatAskResponse)
async def post_message(
    session_id: int,
    req: ChatAskRequest,
    db: AsyncSession = Depends(get_db),
):
    """Ask a question within a conversation. Persists both the user message and
    the RAG-generated assistant answer, then returns the assistant message."""
    session = await _get_session_or_404(session_id, db)

    # Persist the user's message
    user_msg = ChatMessage(session_id=session.id, role="user", content=req.question)
    db.add(user_msg)

    # Title the conversation from its first user message
    if session.title == "New chat":
        session.title = _make_title(req.question)

    await db.commit()

    # Generate the answer via the RAG chain
    try:
        answer = await run_rag_chain(req.question, top_k=req.top_k)
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))

    # Persist the assistant's message
    assistant_msg = ChatMessage(session_id=session.id, role="assistant", content=answer)
    db.add(assistant_msg)
    await db.commit()
    await db.refresh(assistant_msg)

    return ChatAskResponse(
        session_id=session.id,
        title=session.title,
        message=MessageItem.model_validate(assistant_msg),
    )
