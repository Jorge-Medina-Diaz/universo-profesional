"""Profile photo upload + validation + pluggable storage (filesystem or S3)."""
from __future__ import annotations

import io
from typing import Any
from uuid import UUID

import structlog
from PIL import Image
from sqlalchemy.ext.asyncio import AsyncSession

from src.shared.security import utc_now
from src.shared.storage import get_storage
from src.universe.infrastructure.orm import AvatarOrm

logger = structlog.get_logger(__name__)


MAX_BYTES = 5 * 1024 * 1024  # 5 MB
MAX_DIM = 2048
ALLOWED_MIME = {"image/jpeg", "image/png", "image/webp"}
EXT_BY_MIME = {"image/jpeg": "jpg", "image/png": "png", "image/webp": "webp"}


def _avatar_key(filename: str) -> str:
    """Storage key for an avatar — `avatars/<user_id>.<ext>`."""
    return f"avatars/{filename}"


def _validate_and_normalize(data: bytes, mime: str | None) -> tuple[bytes, str, int, int, str]:
    if not mime or mime not in ALLOWED_MIME:
        # Try sniffing
        try:
            img_test = Image.open(io.BytesIO(data))
            fmt = (img_test.format or "").lower()
            if fmt in ("jpeg", "jpg"):
                mime = "image/jpeg"
            elif fmt == "png":
                mime = "image/png"
            elif fmt == "webp":
                mime = "image/webp"
        except Exception as exc:
            raise ValueError(f"Unrecognised image: {exc}") from exc
    if mime not in ALLOWED_MIME:
        raise ValueError(f"Mime {mime} not allowed. Use JPG/PNG/WebP.")
    if len(data) > MAX_BYTES:
        raise ValueError(f"File too large ({len(data)} bytes > {MAX_BYTES}).")

    img = Image.open(io.BytesIO(data))
    img.verify()  # detect malformed images
    img = Image.open(io.BytesIO(data))  # reopen — verify() leaves the file unusable
    w, h = img.size
    if w > MAX_DIM or h > MAX_DIM:
        img.thumbnail((MAX_DIM, MAX_DIM))
        out = io.BytesIO()
        save_fmt = "JPEG" if mime == "image/jpeg" else ("PNG" if mime == "image/png" else "WEBP")
        img.save(out, format=save_fmt, quality=85)
        data = out.getvalue()
        w, h = img.size
    ext = EXT_BY_MIME[mime]
    return data, mime, w, h, ext


async def save_avatar(
    session: AsyncSession,
    *,
    user_id: UUID,
    data: bytes,
    mime: str | None,
    original_filename: str | None,
) -> dict[str, Any]:
    normalized, mime, w, h, ext = _validate_and_normalize(data, mime)
    storage = get_storage()
    filename = f"{user_id}.{ext}"
    # Clean up any previous extension for this user (no listing on the storage
    # port, so delete the other known extensions explicitly).
    for other_ext in EXT_BY_MIME.values():
        if other_ext != ext:
            await storage.delete(_avatar_key(f"{user_id}.{other_ext}"))
    await storage.save(_avatar_key(filename), normalized, content_type=mime)

    existing = await session.get(AvatarOrm, user_id)
    if existing is None:
        session.add(
            AvatarOrm(
                user_id=user_id,
                mime_type=mime,
                size_bytes=len(normalized),
                filename=filename,
                width=w,
                height=h,
                uploaded_at=utc_now(),
            )
        )
    else:
        existing.mime_type = mime
        existing.size_bytes = len(normalized)
        existing.filename = filename
        existing.width = w
        existing.height = h
        existing.uploaded_at = utc_now()
    await session.flush()
    return {
        "mime_type": mime,
        "size_bytes": len(normalized),
        "width": w,
        "height": h,
        "url": "/api/v1/users/me/photo",
    }


async def load_avatar(session: AsyncSession, user_id: UUID) -> tuple[bytes, str] | None:
    row = await session.get(AvatarOrm, user_id)
    if row is None:
        return None
    storage = get_storage()
    key = _avatar_key(row.filename)
    if not await storage.exists(key):
        return None
    return await storage.read(key), row.mime_type


async def delete_avatar(session: AsyncSession, user_id: UUID) -> bool:
    row = await session.get(AvatarOrm, user_id)
    if row is None:
        return False
    try:
        await get_storage().delete(_avatar_key(row.filename))
    except Exception:
        pass
    await session.delete(row)
    await session.flush()
    return True
