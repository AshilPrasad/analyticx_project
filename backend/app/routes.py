"""
routes.py — All API endpoints for the AI Q&A application.

/api/documents/   — Upload, list, and delete documents (the knowledge base)
/api/qa/          — Ask questions (triggers the LangChain RAG chain)
"""

import io
import logging

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from pydantic import BaseModel, Field
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.config import settings
from app.database import IngestedDocument, get_db
from app.rag.chain import run_rag_chain
from app.rag.vectorstore import add_documents, delete_by_source, search_with_scores

logger = logging.getLogger(__name__)

document_router = APIRouter(prefix="/api/documents", tags=["Documents"])
qa_router       = APIRouter(prefix="/api/qa",        tags=["Q&A"])


# ── Schemas ───────────────────────────────────────────────────────────────────

class IngestResponse(BaseModel):
    message: str
    document_name: str
    chunks_created: int


class DocumentItem(BaseModel):
    document_name: str
    chunk_count: int


class QARequest(BaseModel):
    question: str = Field(..., min_length=3, max_length=2000, description="Your question")
    top_k: int    = Field(default=5, ge=1, le=20, description="Number of chunks to retrieve")


class SourceChunk(BaseModel):
    document_name: str
    content: str
    similarity: float


class QAResponse(BaseModel):
    question: str
    answer: str
    sources: list[SourceChunk]
    model: str = settings.LLM_MODEL


# ── Text splitter (LangChain) ─────────────────────────────────────────────────

_splitter = RecursiveCharacterTextSplitter(
    chunk_size=500,
    chunk_overlap=50,
    separators=["\n\n", "\n", ". ", " ", ""],  # tries to split on paragraphs first
)


# ── File extraction helper ────────────────────────────────────────────────────

async def _extract_text(file: UploadFile) -> str:
    """Pull plain text from a .txt or .pdf upload."""
    content = await file.read()
    if file.filename.endswith(".pdf"):
        try:
            from pypdf import PdfReader
            return "\n\n".join(p.extract_text() or "" for p in PdfReader(io.BytesIO(content)).pages)
        except Exception as e:
            raise HTTPException(status_code=422, detail=f"PDF parse error: {e}")
    try:
        return content.decode("utf-8")
    except UnicodeDecodeError:
        return content.decode("latin-1")


# ── Document routes ───────────────────────────────────────────────────────────

@document_router.post("/", response_model=IngestResponse, status_code=201)
async def ingest_document(
    file: UploadFile = File(..., description="Upload a .txt or .pdf file"),
    db: AsyncSession = Depends(get_db),
):
    """
    Upload a document to the knowledge base.

    Pipeline:
      1. Extract text from .txt / .pdf
      2. Split into chunks (LangChain RecursiveCharacterTextSplitter)
      3. Embed + store chunks in PGVector (LangChain)
      4. Save document metadata to PostgreSQL
    """
    name = file.filename or "unnamed"
    raw  = await _extract_text(file)

    if not raw.strip():
        raise HTTPException(status_code=422, detail="Document appears to be empty.")

    # Delete any existing version of this document (upsert behaviour)
    await delete_by_source(name)
    await db.execute(delete(IngestedDocument).where(IngestedDocument.document_name == name))

    # Split with LangChain text splitter
    lc_docs = _splitter.create_documents(
        texts=[raw],
        metadatas=[{"source": name}],
    )

    # Store in PGVector (LangChain manages embeddings + table)
    await add_documents(lc_docs)

    # Save metadata to our tracking table
    db.add(IngestedDocument(document_name=name, chunk_count=len(lc_docs)))
    await db.commit()

    logger.info(f"Ingested '{name}' -> {len(lc_docs)} chunks")
    return IngestResponse(
        message="Ingested successfully.",
        document_name=name,
        chunks_created=len(lc_docs),
    )


@document_router.get("/", response_model=list[DocumentItem])
async def list_documents(db: AsyncSession = Depends(get_db)):
    """List all documents currently in the knowledge base."""
    rows = (await db.execute(select(IngestedDocument))).scalars().all()
    return [
        DocumentItem(document_name=r.document_name, chunk_count=r.chunk_count)
        for r in rows
    ]


@document_router.delete("/{document_name}", status_code=204)
async def delete_document(document_name: str, db: AsyncSession = Depends(get_db)):
    """Remove a document and all its chunks from the knowledge base."""
    # Delete from LangChain PGVector table
    deleted = await delete_by_source(document_name)

    # Delete from metadata table
    result = await db.execute(
        delete(IngestedDocument).where(IngestedDocument.document_name == document_name)
    )
    await db.commit()

    if result.rowcount == 0 and deleted == 0:
        raise HTTPException(status_code=404, detail=f"'{document_name}' not found.")


# ── Q&A route (LangChain RAG chain) ──────────────────────────────────────────

@qa_router.post("/", response_model=QAResponse)
async def answer_question(req: QARequest, db: AsyncSession = Depends(get_db)):
    """
    Answer a question using the LangChain LCEL RAG chain:

      Step 1 — Embed question + retrieve top-K chunks  (rag/vectorstore.py)
      Step 2 — Inject chunks into prompt template       (rag/chain.py)
      Step 3 — Generate answer via Llama 3 on Groq      (rag/llm.py)
    """
    # Run the LCEL RAG chain (returns plain answer string)
    try:
        answer = await run_rag_chain(req.question, top_k=req.top_k)
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))

    # Separately fetch source chunks with similarity scores for attribution
    docs_with_scores = await search_with_scores(req.question, top_k=req.top_k)

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
