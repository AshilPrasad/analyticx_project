"""
api/routes/qa.py — One-shot Q&A endpoint (stateless RAG, scoped per user).

/api/qa/  — ask a question against the current user's documents
"""

import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_current_user
from app.db.models import User
from app.db.session import get_db
from app.rag.chain import run_rag_chain
from app.rag.vectorstore import search_with_scores
from app.schemas.document import QARequest, QAResponse, SourceChunk

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/qa", tags=["Q&A"])


@router.post("/", response_model=QAResponse)
async def answer_question(
    req: QARequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Answer a question using the LangChain LCEL RAG chain (scoped to the user):

      Step 1 — Embed question + retrieve top-K chunks  (rag/vectorstore.py)
      Step 2 — Inject chunks into prompt template       (rag/chain.py)
      Step 3 — Generate answer via Gemini                (rag/llm.py)
    """
    uid = current_user.id
    try:
        answer = await run_rag_chain(req.question, top_k=req.top_k, user_id=uid)
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))

    docs_with_scores = await search_with_scores(req.question, top_k=req.top_k, user_id=uid)

    if not docs_with_scores:
        raise HTTPException(
            status_code=404,
            detail="No documents in the knowledge base. Upload documents first via POST /api/documents/",
        )

    sources = [
        SourceChunk(
            document_name=doc.metadata.get("source", "unknown"),
            content=doc.page_content,
            similarity=round(float(score), 4),
        )
        for doc, score in docs_with_scores
    ]

    return QAResponse(
        question=req.question,
        answer=answer,
        sources=sources,
    )
