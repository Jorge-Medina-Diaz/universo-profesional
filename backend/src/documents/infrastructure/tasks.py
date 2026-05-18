"""Arq tasks for Documents context."""
from __future__ import annotations

from typing import Any
from uuid import UUID

import structlog

from src.documents.infrastructure.renderer import WeasyPrintRenderer
from src.shared.db import get_session_factory

logger = structlog.get_logger(__name__)


async def render_document(
    ctx: dict[str, Any], *, document_id: str, user_id: str
) -> dict[str, str | None]:
    """Re-render an existing document (used for async rendering paths)."""
    from sqlalchemy import select

    from src.documents.infrastructure.orm import DocumentOrm

    renderer = WeasyPrintRenderer()
    factory = get_session_factory()
    async with factory() as session:
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
        await session.commit()
        return {"pdf": pdf, "docx": docx}
