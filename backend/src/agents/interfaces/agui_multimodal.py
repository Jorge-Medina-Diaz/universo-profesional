"""Multimodal attachment extraction for AG-UI endpoints."""
from __future__ import annotations

import asyncio
import io
from typing import Any

from agno.media import Image
from pypdf import PdfReader

from src.agents.interfaces.agui_core import _decode_data_value, _last_user_parts

_MAX_RUN_IMAGES = 3
_MAX_PDF_CHARS = 8000


def _extract_agui_images(messages: list[Any]) -> list[Any]:
    """Build agno Image objects from image InputContent parts (data or url)."""
    images: list[Any] = []
    for part in _last_user_parts(messages):
        if getattr(part, "type", None) != "image":
            continue
        source = getattr(part, "source", None)
        if source is None:
            continue
        value = getattr(source, "value", None)
        if not value:
            continue
        mime = getattr(source, "mime_type", None)
        stype = getattr(source, "type", None)
        try:
            if stype == "url":
                images.append(Image(url=value))
            else:  # "data" (base64)
                images.append(Image(content=_decode_data_value(value), mime_type=mime))
        except Exception:  # skip an unreadable attachment
            continue
        if len(images) >= _MAX_RUN_IMAGES:
            break
    return images


async def _extract_agui_pdf_text(messages: list[Any]) -> str:
    """Inline-parse text from attached PDF document parts (best-effort)."""
    chunks: list[str] = []
    for part in _last_user_parts(messages):
        source = getattr(part, "source", None)
        if source is None:
            continue
        mime = getattr(source, "mime_type", None)
        is_pdf = getattr(part, "type", None) == "document" or mime == "application/pdf"
        if not is_pdf or getattr(source, "type", None) != "data":
            continue
        value = getattr(source, "value", None)
        if not value:
            continue
        try:
            def _parse(pdf_value: str = value) -> str:
                reader = PdfReader(io.BytesIO(_decode_data_value(pdf_value)))
                return "\n".join((pg.extract_text() or "") for pg in reader.pages).strip()

            pdf_text = await asyncio.to_thread(_parse)
            if pdf_text:
                chunks.append("[Documento adjunto]\n" + pdf_text[:_MAX_PDF_CHARS])
        except Exception:  # skip an unreadable PDF
            continue
    return "\n\n".join(chunks)
