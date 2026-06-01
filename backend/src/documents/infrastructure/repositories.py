"""SQLAlchemy implementations of Documents ports."""
from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import desc, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.documents.application.ports import DocumentRepository, JobRepository
from src.documents.domain.entities import Document, Job
from src.documents.infrastructure.orm import DocumentOrm, JobOrm


def _doc_to_domain(row: DocumentOrm) -> Document:
    return Document(
        id=row.id,
        user_id=row.user_id,
        kind=row.kind,
        template=row.template,
        language=row.language,
        tone=row.tone,
        length=row.length,
        job_id=row.job_id,
        generated_from=row.generated_from or {},
        content_json=row.content_json,
        pdf_path=row.pdf_path,
        docx_path=row.docx_path,
        share_token=row.share_token,
        share_expires_at=row.share_expires_at,
        created_at=row.created_at,
        render_status=row.render_status,
    )


class SqlAlchemyDocumentRepository(DocumentRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, document: Document) -> None:
        self._session.add(
            DocumentOrm(
                id=document.id,
                user_id=document.user_id,
                kind=document.kind,
                template=document.template,
                language=document.language,
                tone=document.tone,
                length=document.length,
                job_id=document.job_id,
                generated_from=document.generated_from,
                content_json=document.content_json,
                pdf_path=document.pdf_path,
                docx_path=document.docx_path,
                share_token=document.share_token,
                share_expires_at=document.share_expires_at,
                created_at=document.created_at,
                render_status=document.render_status,
            )
        )
        await self._session.flush()

    async def get(self, user_id: UUID, document_id: UUID) -> Document | None:
        stmt = (
            select(DocumentOrm)
            .where(DocumentOrm.id == document_id)
            .where(DocumentOrm.user_id == user_id)
        )
        row = (await self._session.execute(stmt)).scalar_one_or_none()
        return _doc_to_domain(row) if row else None

    async def list(self, user_id: UUID, kind: str | None = None, limit: int = 20) -> list[Document]:
        stmt = (
            select(DocumentOrm)
            .where(DocumentOrm.user_id == user_id)
            .order_by(desc(DocumentOrm.created_at))
            .limit(limit)
        )
        if kind:
            stmt = stmt.where(DocumentOrm.kind == kind)
        rows = (await self._session.execute(stmt)).scalars().all()
        return [_doc_to_domain(r) for r in rows]

    async def update_renders(
        self,
        document_id: UUID,
        pdf_path: str | None,
        docx_path: str | None,
        render_status: str,
    ) -> None:
        stmt = (
            update(DocumentOrm)
            .where(DocumentOrm.id == document_id)
            .values(pdf_path=pdf_path, docx_path=docx_path, render_status=render_status)
        )
        await self._session.execute(stmt)
        await self._session.flush()

    async def get_by_share_token(self, token: str) -> Document | None:
        stmt = select(DocumentOrm).where(DocumentOrm.share_token == token)
        row = (await self._session.execute(stmt)).scalar_one_or_none()
        return _doc_to_domain(row) if row else None

    async def set_share_token(
        self, document_id: UUID, token: str, expires_at: datetime | None
    ) -> None:
        stmt = (
            update(DocumentOrm)
            .where(DocumentOrm.id == document_id)
            .values(share_token=token, share_expires_at=expires_at)
        )
        await self._session.execute(stmt)
        await self._session.flush()


class SqlAlchemyJobRepository(JobRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, job: Job) -> None:
        self._session.add(
            JobOrm(
                id=job.id,
                user_id=job.user_id,
                company_name=job.company_name,
                title=job.title,
                url=job.url,
                description_raw=job.description_raw,
                description_parsed=job.description_parsed,
                ats_detected=job.ats_detected,
                embedding=job.embedding,
                created_at=job.created_at,
            )
        )
        await self._session.flush()

    async def get(self, user_id: UUID, job_id: UUID) -> Job | None:
        stmt = (
            select(JobOrm)
            .where(JobOrm.id == job_id)
            .where(JobOrm.user_id == user_id)
        )
        row = (await self._session.execute(stmt)).scalar_one_or_none()
        if row is None:
            return None
        return Job(
            id=row.id,
            user_id=row.user_id,
            company_name=row.company_name,
            title=row.title,
            url=row.url,
            description_raw=row.description_raw,
            description_parsed=row.description_parsed or {},
            ats_detected=row.ats_detected,
            embedding=list(row.embedding) if row.embedding is not None else None,
            created_at=row.created_at,
        )
