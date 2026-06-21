"""
chain.py — LangChain LCEL RAG chain (Retrieval-Augmented Generation).

What it does in plain English:
  The chain wires together three steps into one callable pipeline:

  Question
    │
    ▼
  [1] Retriever (vectorstore.py)
      Converts the question to a vector and finds the top-K similar chunks
    │
    ▼
  [2] Prompt (ChatPromptTemplate)
      Injects the retrieved chunks as context into a structured prompt
    │
    ▼
  [3] LLM (llm.py — Google Gemini)
      Reads the prompt and generates a grounded answer
    │
    ▼
  Answer (string)

This is built with LangChain's LCEL (LangChain Expression Language)
using the | pipe operator, similar to Unix pipes.
"""

import asyncio
import logging

from langchain_core.documents import Document
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough

from app.rag.llm import get_llm
from app.rag.vectorstore import get_vectorstore, user_filter

logger = logging.getLogger(__name__)


# ── Prompt template ───────────────────────────────────────────────────────────

RAG_PROMPT = ChatPromptTemplate.from_messages([
    (
        "system",
        """You are a helpful AI assistant. Answer the user's question based ONLY \
on the following context retrieved from their documents.

Rules:
- If the context does not contain enough information, say: "I don't have enough \
information in the provided documents to answer this question."
- Do NOT make up facts or use knowledge outside the context.
- Be concise and accurate.

Context:
{context}""",
    ),
    ("human", "{question}"),
])


# ── Helper ────────────────────────────────────────────────────────────────────

def _format_docs(docs: list[Document]) -> str:
    """Format retrieved documents into a single context string."""
    return "\n\n---\n\n".join(
        f"[Source: {doc.metadata.get('source', 'unknown')}]\n{doc.page_content}"
        for doc in docs
    )


# ── RAG chain builder ─────────────────────────────────────────────────────────

def build_rag_chain(top_k: int = 5, user_id: int | None = None):
    """
    Build and return a LangChain LCEL RAG chain, scoped to one user's documents.

    LCEL chain (read left to right with | pipe operator):

        {context: retriever | format_docs, question: passthrough}
            | RAG_PROMPT
            | LLM (Gemini)
            | StrOutputParser()   ← extracts plain string from LLM response

    Args:
        top_k: Number of document chunks to retrieve for context.
        user_id: Restrict retrieval to this user's documents.

    Returns:
        A Runnable that accepts a question string and returns an answer string.
    """
    search_kwargs = {"k": top_k}
    flt = user_filter(user_id)
    if flt is not None:
        search_kwargs["filter"] = flt

    retriever = get_vectorstore().as_retriever(
        search_type="similarity",
        search_kwargs=search_kwargs,
    )

    chain = (
        {"context": retriever | _format_docs, "question": RunnablePassthrough()}
        | RAG_PROMPT
        | get_llm()
        | StrOutputParser()
    )

    return chain


async def run_rag_chain(question: str, top_k: int = 5, user_id: int | None = None) -> str:
    """
    Run the RAG chain asynchronously, scoped to one user's documents.
    LangChain's sync chain is wrapped in asyncio.to_thread to avoid blocking.

    Args:
        question: The user's natural language question.
        top_k:    Number of document chunks to use as context.
        user_id:  Restrict retrieval to this user's documents.

    Returns:
        The LLM-generated answer string.
    """
    chain = build_rag_chain(top_k=top_k, user_id=user_id)
    logger.info(f"Running RAG chain (user={user_id}): '{question[:60]}...'")
    answer = await asyncio.to_thread(chain.invoke, question)
    return answer
