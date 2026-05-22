"""Documents context ports."""
from __future__ import annotations

from typing import Any, Protocol
from uuid import UUID

from src.documents.domain.entities import Document, Job


class DocumentRepository(Protocol):
    async def add(self, document: Document) -> None: ...
    async def get(self, user_id: UUID, document_id: UUID) -> Document | None: ...
    async def list(self, user_id: UUID, kind: str | None = None, limit: int = 20) -> list[Document]: ...
    async def update_renders(
        self, document_id: UUID, pdf_path: str | None, docx_path: str | None
    ) -> None: ...
    async def get_by_share_token(self, token: str) -> Document | None: ...
    async def set_share_token(
        self, document_id: UUID, token: str, expires_at: Any | None
    ) -> None: ...


class JobRepository(Protocol):
    async def add(self, job: Job) -> None: ...
    async def get(self, user_id: UUID, job_id: UUID) -> Job | None: ...


class JobParser(Protocol):
    async def parse(self, *, url: str | None, description: str | None) -> dict[str, Any]: ...


class LlmClient(Protocol):
    async def generate_cv_bullets(
        self,
        *,
        job_summary: dict[str, Any],
        retrieved: list[dict[str, Any]],
        language: str,
        tone: str | None,
    ) -> dict[str, Any]:
        """Return a JSON Resume v1.0.0-shaped object."""
        ...

    async def generate_cover_letter(
        self,
        *,
        job_summary: dict[str, Any],
        retrieved: list[dict[str, Any]],
        language: str,
        tone: str | None,
    ) -> dict[str, Any]:
        """Return a JSON Resume-shaped object whose `basics.summary` is the
        cover-letter body. Renderer can pick this up via a dedicated template
        in the future; for now the body is also exposed at top-level
        `cover_letter_body` so the frontend can display it directly."""
        ...


class Renderer(Protocol):
    async def render_pdf(
        self, *, content_json: dict[str, Any], template: str, language: str, user_id: UUID
    ) -> str: ...
    async def render_docx(
        self, *, content_json: dict[str, Any], template: str, language: str, user_id: UUID
    ) -> str: ...


class StoragePort(Protocol):
    def url_for(self, path: str) -> str: ...
    def read(self, path: str) -> bytes: ...
