"""
api/routes/documents.py — Knowledge-base document management.

/api/documents/   — upload, list, and delete documents (scoped per user)
"""

import io
import logging

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from langchain_text_splitters import RecursiveCharacterTextSplitter
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_current_user
from app.db.models import IngestedDocument, User
from app.db.session import get_db
from app.rag.vectorstore import add_documents, delete_by_source
from app.schemas.document import DocumentItem, IngestResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/documents", tags=["Documents"])

_splitter = RecursiveCharacterTextSplitter(
    chunk_size=500,
    chunk_overlap=50,
    separators=["\n\n", "\n", ". ", " ", ""],  # tries to split on paragraphs first
)


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


@router.post("/", response_model=IngestResponse, status_code=201)
async def ingest_document(
    file: UploadFile = File(..., description="Upload a .txt or .pdf file"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Upload a document to the current user's knowledge base.

    Pipeline:
      1. Extract text from .txt / .pdf
      2. Split into chunks (LangChain RecursiveCharacterTextSplitter)
      3. Embed + store chunks in PGVector (tagged with the user's id)
      4. Save document metadata to PostgreSQL
    """
    uid = current_user.id
    name = file.filename or "unnamed"
    raw = await _extract_text(file)

    if not raw.strip():
        raise HTTPException(status_code=422, detail="Document appears to be empty.")

    # Delete any existing version of this document for this user (upsert behaviour)
    await delete_by_source(name, user_id=uid)
    await db.execute(
        delete(IngestedDocument).where(
            IngestedDocument.document_name == name,
            IngestedDocument.user_id == uid,
        )
    )

    # Split with LangChain text splitter (tag each chunk with the owner)
    lc_docs = _splitter.create_documents(
        texts=[raw],
        metadatas=[{"source": name, "user_id": str(uid)}],
    )

    # Store in PGVector (LangChain manages embeddings + table)
    await add_documents(lc_docs)

    # Save metadata to our tracking table
    db.add(IngestedDocument(user_id=uid, document_name=name, chunk_count=len(lc_docs)))
    await db.commit()

    logger.info(f"Ingested '{name}' -> {len(lc_docs)} chunks (user={uid})")
    return IngestResponse(
        message="Ingested successfully.",
        document_name=name,
        chunks_created=len(lc_docs),
    )


@router.get("/", response_model=list[DocumentItem])
async def list_documents(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List documents in the current user's knowledge base."""
    rows = (
        await db.execute(
            select(IngestedDocument).where(IngestedDocument.user_id == current_user.id)
        )
    ).scalars().all()
    return [
        DocumentItem(document_name=r.document_name, chunk_count=r.chunk_count)
        for r in rows
    ]


@router.delete("/{document_name}", status_code=204)
async def delete_document(
    document_name: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Remove a document and all its chunks from the current user's knowledge base."""
    uid = current_user.id
    deleted = await delete_by_source(document_name, user_id=uid)

    result = await db.execute(
        delete(IngestedDocument).where(
            IngestedDocument.document_name == document_name,
            IngestedDocument.user_id == uid,
        )
    )
    await db.commit()

    if result.rowcount == 0 and deleted == 0:
        raise HTTPException(status_code=404, detail=f"'{document_name}' not found.")
