"""/api/v1/knowledge/* — upload + list + search the knowledge store.

Memory layer 4: long unstructured documents (papers, PDFs, notes) that the
agent can recall via `search_knowledge`. Uploads are ingested as a raw
substrate AND queued for coherence extraction (entities into the universe).
"""
from __future__ import annotations

from typing import Any
from uuid import UUID

import structlog
from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from pydantic import BaseModel

from src.identity.interfaces.api.deps import CurrentUserId, SessionDep
from src.knowledge.application.use_cases import (
    ingest_document,
    list_documents,
    search_knowledge,
)
from src.shared.uow import unit_of_work

logger = structlog.get_logger(__name__)

router = APIRouter()

_MAX_UPLOAD_BYTES = 20 * 1024 * 1024  # 20 MB
_ALLOWED = {
    "application/pdf",
    "text/plain",
    "text/markdown",
    "text/x-markdown",
}


def _extract_text(contents: bytes, mime: str | None, filename: str) -> str:
    if mime == "application/pdf" or filename.lower().endswith(".pdf"):
        from src.integrations.application.pdf_cv_parser import extract_pdf_text

        full, _pages = extract_pdf_text(contents)
        return full
    # text / markdown
    try:
        return contents.decode("utf-8", errors="replace")
    except Exception:
        return ""


@router.post("/upload")
async def upload_document(
    user_id: CurrentUserId,
    session: SessionDep,
    file: UploadFile = File(...),
    title: str | None = Form(default=None),
    tags: str | None = Form(default=None),  # comma-separated
) -> dict[str, Any]:
    contents = await file.read()
    if len(contents) > _MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"file exceeds {_MAX_UPLOAD_BYTES // (1024 * 1024)} MB limit",
        )
    if file.content_type and file.content_type not in _ALLOWED:
        raise HTTPException(
            status_code=400,
            detail=f"unsupported type {file.content_type!r} (pdf/txt/md only)",
        )
    body = _extract_text(contents, file.content_type, file.filename or "")
    if not body.strip():
        raise HTTPException(status_code=400, detail="no extractable text in file")

    tag_list = [t.strip() for t in (tags or "").split(",") if t.strip()]
    uid = UUID(user_id)
    async with unit_of_work(session) as uow:
        doc_id = await ingest_document(
            session,
            user_id=uid,
            title=title or (file.filename or "documento"),
            body=body,
            source="upload",
            mime=file.content_type,
            tags=tag_list,
        )
        await uow.commit()
    if doc_id is None:
        raise HTTPException(status_code=400, detail="nothing to ingest")

    # Coherence half: queue entity extraction from the document text so the
    # universe (source of truth) absorbs what's in the substrate.
    try:
        from src.integrations.infrastructure.queue import enqueue_integration_task

        await enqueue_integration_task(
            "extract_knowledge_document", user_id=user_id, document_id=str(doc_id)
        )
        queued = True
        extraction_warning: str | None = None
    except Exception as exc:
        queued = False
        logger.warning(
            "knowledge_extraction_enqueue_failed",
            document_id=str(doc_id),
            error=str(exc),
        )
        extraction_warning = (
            "El documento se guardó, pero la extracción automática no pudo "
            "encolarse. Vuelve a intentarlo más tarde."
        )

    result: dict[str, Any] = {"document_id": str(doc_id), "extraction_queued": queued}
    if extraction_warning:
        result["extraction_warning"] = extraction_warning
    return result


@router.get("/documents")
async def get_documents(
    user_id: CurrentUserId, session: SessionDep
) -> dict[str, Any]:
    docs = await list_documents(session, user_id=UUID(user_id))
    return {"documents": docs}


class KnowledgeSearchBody(BaseModel):
    query: str
    top_k: int = 5
    tags: list[str] | None = None


@router.post("/search")
async def search(
    user_id: CurrentUserId, session: SessionDep, body: KnowledgeSearchBody
) -> dict[str, Any]:
    results = await search_knowledge(
        session,
        user_id=UUID(user_id),
        query=body.query,
        top_k=body.top_k,
        tags=body.tags,
    )
    return {"results": results}
