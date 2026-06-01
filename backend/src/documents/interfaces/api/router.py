"""Documents REST API: /api/v1/documents/*"""
from __future__ import annotations

from datetime import UTC
from pathlib import Path
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel, Field

from src.documents.application.use_cases import (
    GenerateCv,
    GenerateCvInput,
    GetDocument,
    ListDocuments,
    ShareDocument,
)
from src.documents.infrastructure.job_parser import MockJobParser
from src.documents.infrastructure.llm_client import build_document_llm_client
from src.documents.infrastructure.renderer import WeasyPrintRenderer
from src.documents.infrastructure.repositories import (
    SqlAlchemyDocumentRepository,
    SqlAlchemyJobRepository,
)
from src.identity.interfaces.api.deps import CurrentUserId, SessionDep, current_user_id
from src.shared.embeddings import get_embeddings_service
from src.shared.metrics import cv_generated_total
from src.shared.storage import get_storage
from src.shared.uow import unit_of_work
from src.universe.infrastructure.semantic_search import PgVectorSemanticSearch

router = APIRouter()


class GenerateCvRequest(BaseModel):
    job_url: str | None = None
    job_description: str | None = Field(default=None, max_length=20000)
    template: str = "ats-classic"
    language: str = Field(default="es", max_length=2)
    tone: str = "professional"
    length: str = "1-page"
    kind: str = Field(default="cv", pattern="^(cv|cover_letter)$")


def _generate_cv_dep(
    session: SessionDep,
    user_id: str = Depends(current_user_id),
) -> GenerateCv:
    return GenerateCv(
        documents=SqlAlchemyDocumentRepository(session),
        jobs=SqlAlchemyJobRepository(session),
        parser=MockJobParser(),
        embedder=get_embeddings_service(),
        search=PgVectorSemanticSearch(session),
        llm=build_document_llm_client(session, user_id=UUID(user_id)),
        renderer=WeasyPrintRenderer(),
    )


def _list_docs_dep(session: SessionDep) -> ListDocuments:
    return ListDocuments(SqlAlchemyDocumentRepository(session))


def _get_doc_dep(session: SessionDep) -> GetDocument:
    return GetDocument(SqlAlchemyDocumentRepository(session))


def _share_doc_dep(session: SessionDep) -> ShareDocument:
    return ShareDocument(SqlAlchemyDocumentRepository(session))


GenerateCvDep = Annotated[GenerateCv, Depends(_generate_cv_dep)]
ListDocsDep = Annotated[ListDocuments, Depends(_list_docs_dep)]
GetDocDep = Annotated[GetDocument, Depends(_get_doc_dep)]
ShareDocDep = Annotated[ShareDocument, Depends(_share_doc_dep)]


@router.post("/generate-cv", status_code=status.HTTP_201_CREATED)
async def generate_cv(
    user_id: CurrentUserId,
    body: GenerateCvRequest,
    uc: GenerateCvDep,
    session: SessionDep,
) -> dict[str, Any]:
    # Quota check (Free plan)
    from src.billing.application.use_cases import CheckQuota
    from src.billing.infrastructure.repositories import (
        SqlAlchemyQuotaRepository,
        SqlAlchemySubscriptionRepository,
    )

    quota = CheckQuota(
        SqlAlchemySubscriptionRepository(session),
        SqlAlchemyQuotaRepository(session),
    )
    # Cover letters have their own monthly cap (monthly_cover_letters) — without
    # this branch a Free user could mint unlimited cover letters under the CV cap.
    quota_resource = (
        "cover_letter_generated" if body.kind == "cover_letter" else "cv_generated"
    )
    quota_result = await quota.execute(user_id=user_id, resource=quota_resource)
    if quota_result.is_failure:
        raise quota_result.error  # type: ignore[union-attr]

    async with unit_of_work(session) as uow:
        result = await uc.execute(
            user_id=user_id,
            payload=GenerateCvInput(
                job_url=body.job_url,
                job_description=body.job_description,
                template=body.template,
                language=body.language,
                tone=body.tone,
                length=body.length,
                kind=body.kind,
            ),
            uow=uow,
        )
        if result.is_failure:
            raise result.error  # type: ignore[union-attr]
        # Increment the matching quota bucket (CV vs cover letter).
        await quota.increment(user_id=user_id, resource=quota_resource)
        await uow.commit()
        dto = result.value  # type: ignore[union-attr]
        cv_generated_total.labels(kind=body.kind).inc()
    return {
        "document_id": dto.document_id,
        "pdf_url": dto.pdf_url,
        "docx_url": dto.docx_url,
        "json_resume": dto.json_resume,
        "render_status": dto.render_status,
    }


@router.get("")
async def list_documents(
    user_id: CurrentUserId,
    uc: ListDocsDep,
    kind: str | None = None,
    limit: int = 20,
) -> list[dict[str, Any]]:
    return await uc.execute(user_id=user_id, kind=kind, limit=limit)


@router.get("/{document_id}")
async def get_document(
    document_id: str,
    user_id: CurrentUserId,
    uc: GetDocDep,
) -> dict[str, Any]:
    result = await uc.execute(user_id=user_id, document_id=document_id)
    if result.is_failure:
        raise result.error  # type: ignore[union-attr]
    return result.value


async def _read_blob_or_404(key: str | None, *, not_found: str) -> bytes:
    storage = get_storage()
    if not key or not await storage.exists(key):
        raise HTTPException(status_code=404, detail=not_found)
    return await storage.read(key)


@router.get("/{document_id}/pdf")
async def download_pdf(
    document_id: str,
    user_id: CurrentUserId,
    uc: GetDocDep,
    session: SessionDep,
) -> Response:
    from uuid import UUID

    from sqlalchemy import select

    from src.documents.infrastructure.orm import DocumentOrm

    row = (
        await session.execute(
            select(DocumentOrm)
            .where(DocumentOrm.id == UUID(document_id))
            .where(DocumentOrm.user_id == UUID(user_id))
        )
    ).scalar_one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail="PDF not found")
    data = await _read_blob_or_404(row.pdf_path, not_found="PDF not found")
    suffix = Path(row.pdf_path).suffix.lower() or ".pdf"
    media = "application/pdf" if suffix == ".pdf" else "text/html"
    return Response(
        content=data,
        media_type=media,
        headers={"Content-Disposition": f'attachment; filename="cv-{document_id}{suffix}"'},
    )


@router.get("/{document_id}/docx")
async def download_docx(
    document_id: str,
    user_id: CurrentUserId,
    session: SessionDep,
) -> Response:
    from uuid import UUID

    from sqlalchemy import select

    from src.documents.infrastructure.orm import DocumentOrm

    row = (
        await session.execute(
            select(DocumentOrm)
            .where(DocumentOrm.id == UUID(document_id))
            .where(DocumentOrm.user_id == UUID(user_id))
        )
    ).scalar_one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail="DOCX not found")
    data = await _read_blob_or_404(row.docx_path, not_found="DOCX not found")
    return Response(
        content=data,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": f'attachment; filename="cv-{document_id}.docx"'},
    )


@router.get("/{document_id}/json")
async def download_json(
    document_id: str,
    user_id: CurrentUserId,
    uc: GetDocDep,
) -> JSONResponse:
    result = await uc.execute(user_id=user_id, document_id=document_id)
    if result.is_failure:
        raise result.error  # type: ignore[union-attr]
    doc = result.value  # type: ignore[union-attr]
    return JSONResponse(
        content=doc["content_json"],
        headers={"Content-Disposition": f'attachment; filename="cv-{document_id}.json"'},
    )


@router.get("/{document_id}/europass")
async def download_europass(
    document_id: str,
    user_id: CurrentUserId,
    uc: GetDocDep,
) -> JSONResponse:
    """Download the CV mapped to the Europass CV JSON model."""
    from src.documents.application.europass import to_europass

    result = await uc.execute(user_id=user_id, document_id=document_id)
    if result.is_failure:
        raise result.error  # type: ignore[union-attr]
    doc = result.value  # type: ignore[union-attr]
    europass = to_europass(doc["content_json"])
    return JSONResponse(
        content=europass,
        headers={
            "Content-Disposition": f'attachment; filename="europass-cv-{document_id}.json"'
        },
    )


@router.post("/{document_id}/share")
async def share_document(
    document_id: str,
    user_id: CurrentUserId,
    uc: ShareDocDep,
    session: SessionDep,
) -> dict[str, str]:
    async with unit_of_work(session) as uow:
        result = await uc.execute(user_id=user_id, document_id=document_id, expires_in_days=30)
        if result.is_failure:
            raise result.error  # type: ignore[union-attr]
        await uow.commit()
        return result.value


# Public router — no auth, resolves a share token to a document summary.
# Mounted at /api/v1/share/{token} from main.py.
public_router = APIRouter()


@public_router.get("/{token}")
async def resolve_share_token(token: str, session: SessionDep) -> dict[str, Any]:
    from datetime import datetime

    repo = SqlAlchemyDocumentRepository(session)
    doc = await repo.get_by_share_token(token)
    if doc is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="not_found")
    # Optional expiry — repository row also stores `share_expires_at`.
    # The isinstance guard makes the comparison type-safe, so no try/except is
    # needed; a previous bare `except Exception: pass` swallowed the 410 itself
    # and served expired links forever.
    expires_raw = getattr(doc, "share_expires_at", None)
    if isinstance(expires_raw, datetime) and expires_raw < datetime.now(UTC):
        raise HTTPException(status_code=status.HTTP_410_GONE, detail="expired")
    return {
        "document_id": str(doc.id),
        "kind": doc.kind,
        "template": doc.template,
        "language": doc.language,
        "created_at": doc.created_at.isoformat() if doc.created_at else None,
        "json_resume": doc.content_json,
        "pdf_url": f"/api/v1/share/{token}/pdf" if doc.pdf_path else None,
        "render_status": getattr(doc, "render_status", "ready"),
    }


@public_router.get("/{token}/pdf")
async def get_share_pdf(token: str, session: SessionDep) -> Response:
    repo = SqlAlchemyDocumentRepository(session)
    doc = await repo.get_by_share_token(token)
    if doc is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    data = await _read_blob_or_404(doc.pdf_path, not_found="not_found")
    suffix = Path(doc.pdf_path).suffix.lower() or ".pdf"
    media = "application/pdf" if suffix == ".pdf" else "text/html"
    return Response(
        content=data,
        media_type=media,
        headers={"Content-Disposition": f'attachment; filename="cv-{doc.id}{suffix}"'},
    )
