"""Document & Job entities. Documents are immutable once generated."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, ClassVar
from uuid import UUID, uuid4

from src.shared.events import DomainEvent


@dataclass(frozen=True, kw_only=True)
class DocumentGenerated(DomainEvent):
    event_type: ClassVar[str] = "documents.generated"
    document_id_str: str = ""
    kind: str = "cv"


@dataclass
class Document:
    id: UUID
    user_id: UUID
    kind: str  # cv | cover_letter
    template: str
    language: str  # ISO 639-1 (2 chars)
    tone: str | None
    length: str | None  # 1-page, 2-page
    job_id: UUID | None
    generated_from: dict[str, Any]
    content_json: dict[str, Any]
    pdf_path: str | None
    docx_path: str | None
    share_token: str | None
    share_expires_at: datetime | None
    created_at: datetime
    _events: list[DomainEvent] = field(default_factory=list, repr=False, compare=False)

    @classmethod
    def create(
        cls,
        *,
        user_id: UUID,
        kind: str,
        template: str,
        language: str,
        tone: str | None,
        length: str | None,
        job_id: UUID | None,
        generated_from: dict[str, Any],
        content_json: dict[str, Any],
        now: datetime,
    ) -> "Document":
        doc = cls(
            id=uuid4(),
            user_id=user_id,
            kind=kind,
            template=template,
            language=language,
            tone=tone,
            length=length,
            job_id=job_id,
            generated_from=generated_from,
            content_json=content_json,
            pdf_path=None,
            docx_path=None,
            share_token=None,
            share_expires_at=None,
            created_at=now,
        )
        doc._events.append(
            DocumentGenerated(user_id=user_id, document_id_str=str(doc.id), kind=kind)
        )
        return doc

    def attach_renders(self, *, pdf_path: str | None, docx_path: str | None) -> None:
        self.pdf_path = pdf_path
        self.docx_path = docx_path

    def make_share_token(self, *, token: str, expires_at: datetime | None) -> None:
        self.share_token = token
        self.share_expires_at = expires_at

    def pop_events(self) -> list[DomainEvent]:
        out = list(self._events)
        self._events.clear()
        return out


@dataclass
class Job:
    id: UUID
    user_id: UUID
    company_name: str | None
    title: str | None
    url: str | None
    description_raw: str
    description_parsed: dict[str, Any]
    ats_detected: str | None
    embedding: list[float] | None
    created_at: datetime

    @classmethod
    def create(
        cls,
        *,
        user_id: UUID,
        description_raw: str,
        company_name: str | None = None,
        title: str | None = None,
        url: str | None = None,
        description_parsed: dict[str, Any] | None = None,
        ats_detected: str | None = None,
        now: datetime,
    ) -> "Job":
        return cls(
            id=uuid4(),
            user_id=user_id,
            company_name=company_name,
            title=title,
            url=url,
            description_raw=description_raw,
            description_parsed=description_parsed or {},
            ats_detected=ats_detected,
            embedding=None,
            created_at=now,
        )
