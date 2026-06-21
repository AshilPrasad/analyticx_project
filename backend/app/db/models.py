"""
db/models.py — SQLAlchemy ORM models.

LangChain PGVector manages its own embedding tables (langchain_pg_collection,
langchain_pg_embedding). These models cover application data:
  - User             : an authenticated account
  - IngestedDocument : a document in a user's knowledge base (metadata only)
  - ChatSession      : a ChatGPT-style conversation
  - ChatMessage      : a single message within a session
"""

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db.base import Base


class User(Base):
    """An application user (authentication)."""
    __tablename__ = "users"

    id              = Column(Integer, primary_key=True)
    email           = Column(String(255), nullable=False, unique=True, index=True)
    name            = Column(String(120), nullable=True)
    hashed_password = Column(String(255), nullable=False)
    created_at      = Column(DateTime(timezone=True), server_default=func.now())


class IngestedDocument(Base):
    """Tracks documents uploaded to the knowledge base (metadata only, no embeddings)."""
    __tablename__ = "ingested_documents"

    id            = Column(Integer, primary_key=True)
    user_id       = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True)
    document_name = Column(String(512), nullable=False)
    chunk_count   = Column(Integer, nullable=False, default=0)
    created_at    = Column(DateTime(timezone=True), server_default=func.now())


class ChatSession(Base):
    """A ChatGPT-style conversation thread."""
    __tablename__ = "chat_sessions"

    id         = Column(Integer, primary_key=True)
    user_id    = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True)
    title      = Column(String(255), nullable=False, default="New chat")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    messages = relationship(
        "ChatMessage",
        back_populates="session",
        cascade="all, delete-orphan",
        order_by="ChatMessage.id",
    )


class ChatMessage(Base):
    """A single message (user question or assistant answer) within a session."""
    __tablename__ = "chat_messages"

    id         = Column(Integer, primary_key=True)
    session_id = Column(
        Integer,
        ForeignKey("chat_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    role       = Column(String(16), nullable=False)  # 'user' | 'assistant'
    content    = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    session = relationship("ChatSession", back_populates="messages")
