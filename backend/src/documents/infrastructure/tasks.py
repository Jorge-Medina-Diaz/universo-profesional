"""Arq tasks for Documents context."""
from __future__ import annotations

from typing import Any
from uuid import UUID

import structlog

from src.documents.infrastructure.renderer import WeasyPrintRenderer
from src.shared.db import with_user_session

logger = structlog.get_logger(__name__)


async def render_document(
    ctx: dict[str, Any], *, document_id: str, user_id: str
) -> dict[str, str | None]:
    """Re-render an existing document (used for async rendering paths)."""
    from sqlalchemy import select

    from src.documents.domain.entities import Document
    from src.documents.infrastructure.orm import DocumentOrm

    renderer = WeasyPrintRenderer()
    # MUST run in the owner's RLS scope: `documents` is FORCE RLS (0039). A raw
    # get_session_factory() session is GUC-less, so the SELECT below returned 0
    # rows and the task silently produced {"pdf": None} for every user — the
    # exact no-op class fixed earlier in universe/infrastructure/tasks.py.
    async with with_user_session(UUID(user_id)) as session:
        row = (
            await session.execute(
                select(DocumentOrm).where(DocumentOrm.id == UUID(document_id))
            )
        ).scalar_one_or_none()
        if row is None:
            return {"pdf": None, "docx": None}
        pdf = await renderer.render_pdf(
            content_json=row.content_json,
            template=row.template,
            language=row.language,
            user_id=UUID(user_id),
        )
        docx = await renderer.render_docx(
            content_json=row.content_json,
            template=row.template,
            language=row.language,
            user_id=UUID(user_id),
        )
        row.pdf_path = pdf
        row.docx_path = docx
        row.render_status = Document.derive_render_status(pdf)
        await session.commit()
        return {"pdf": pdf, "docx": docx, "render_status": row.render_status}
