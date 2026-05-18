"""Documents REST API: /api/v1/documents/*"""
from __future__ import annotations

from pathlib import Path
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, Field

from src.documents.application.use_cases import (
    GenerateCv,
    GenerateCvInput,
    GetDocument,
    ListDocuments,
    ShareDocument,
)
from src.documents.infrastructure.job_parser import MockJobParser
from src.documents.infrastructure.llm_client import MockLlmClient
from src.documents.infrastructure.renderer import WeasyPrintRenderer
from src.documents.infrastructure.repositories import (
    SqlAlchemyDocumentRepository,
    SqlAlchemyJobRepository,
)
from src.identity.interfaces.api.deps import CurrentUserId, SessionDep
from src.shared.embeddings import get_embeddings_service
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


def _generate_cv_dep(session: SessionDep) -> GenerateCv:
    return GenerateCv(
        documents=SqlAlchemyDocumentRepository(session),
        jobs=SqlAlchemyJobRepository(session),
        parser=MockJobParser(),
        embedder=get_embeddings_service(),
        search=PgVectorSemanticSearch(session),
        llm=MockLlmClient(session),
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
    quota_result = await quota.execute(user_id=user_id, resource="cv_generated")
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
            ),
            uow=uow,
        )
        if result.is_failure:
            raise result.error  # type: ignore[union-attr]
        # Increment quota
        await quota.increment(user_id=user_id, resource="cv_generated")
        await uow.commit()
        dto = result.value  # type: ignore[union-attr]
    return {
        "document_id": dto.document_id,
        "pdf_url": dto.pdf_url,
        "docx_url": dto.docx_url,
        "json_resume": dto.json_resume,
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
    return result.value  # type: ignore[union-attr, return-value]


@router.get("/{document_id}/pdf")
async def download_pdf(
    document_id: str,
    user_id: CurrentUserId,
    uc: GetDocDep,
    session: SessionDep,
) -> FileResponse:
    from src.documents.infrastructure.orm import DocumentOrm
    from sqlalchemy import select
    from uuid import UUID

    row = (
        await session.execute(
            select(DocumentOrm)
            .where(DocumentOrm.id == UUID(document_id))
            .where(DocumentOrm.user_id == UUID(user_id))
        )
    ).scalar_one_or_none()
    if row is None or not row.pdf_path or not Path(row.pdf_path).exists():
        raise HTTPException(status_code=404, detail="PDF not found")
    suffix = Path(row.pdf_path).suffix.lower() or ".pdf"
    media = "application/pdf" if suffix == ".pdf" else "text/html"
    return FileResponse(row.pdf_path, media_type=media, filename=f"cv-{document_id}{suffix}")


@router.get("/{document_id}/docx")
async def download_docx(
    document_id: str,
    user_id: CurrentUserId,
    session: SessionDep,
) -> FileResponse:
    from src.documents.infrastructure.orm import DocumentOrm
    from sqlalchemy import select
    from uuid import UUID

    row = (
        await session.execute(
            select(DocumentOrm)
            .where(DocumentOrm.id == UUID(document_id))
            .where(DocumentOrm.user_id == UUID(user_id))
        )
    ).scalar_one_or_none()
    if row is None or not row.docx_path or not Path(row.docx_path).exists():
        raise HTTPException(status_code=404, detail="DOCX not found")
    return FileResponse(
        row.docx_path,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        filename=f"cv-{document_id}.docx",
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
        return result.value  # type: ignore[union-attr, return-value]
