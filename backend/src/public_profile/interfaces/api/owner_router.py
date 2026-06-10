"""Owner-side twin API: configuration, curation, slug lifecycle, analytics.

GET  /api/v1/twin        → config + visitor stats
PUT  /api/v1/twin        → upsert enabled/curation (slug minted on first enable)
POST /api/v1/twin/slug   → regenerate (revokes the old public URL instantly)
"""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel, Field
from sqlalchemy import text

from src.identity.interfaces.api.deps import CurrentUserId, SessionDep
from src.public_profile.application.twin_service import (
    ALLOWED_PUBLIC_KINDS,
    DEFAULT_CHARTER,
    new_slug,
    validate_vanity_slug,
    visible_kinds,
)

router = APIRouter()


class TwinCuration(BaseModel):
    visible_kinds: list[str] = Field(default_factory=lambda: list(ALLOWED_PUBLIC_KINDS))
    charter: str = Field(default=DEFAULT_CHARTER, max_length=500)
    suggested_questions: list[str] = Field(default_factory=list, max_length=5)


class TwinUpdate(BaseModel):
    enabled: bool | None = None
    slug: str | None = Field(default=None, max_length=40)
    curation: TwinCuration | None = None


async def _stats(session: Any, user_id: str) -> dict[str, Any]:
    sessions_7d = (
        await session.execute(
            text(
                "SELECT count(*) FROM twin_sessions WHERE user_id = :uid "
                "AND started_at > now() - interval '7 days'"
            ),
            {"uid": user_id},
        )
    ).scalar()
    questions = (
        await session.execute(
            text(
                "SELECT question, created_at FROM twin_questions WHERE user_id = :uid "
                "ORDER BY created_at DESC LIMIT 10"
            ),
            {"uid": user_id},
        )
    ).all()
    leads = (
        await session.execute(
            text(
                "SELECT contact, message, created_at FROM twin_leads "
                "WHERE user_id = :uid ORDER BY created_at DESC LIMIT 10"
            ),
            {"uid": user_id},
        )
    ).all()
    return {
        "sessions_7d": int(sessions_7d or 0),
        "recent_questions": [
            {"question": q.question, "at": q.created_at.isoformat()} for q in questions
        ],
        "leads": [
            {"contact": l.contact, "message": l.message, "at": l.created_at.isoformat()}
            for l in leads
        ],
    }


@router.get("")
async def get_twin(user_id: CurrentUserId, session: SessionDep) -> dict[str, Any]:
    row = (
        await session.execute(
            text(
                "SELECT slug, enabled, curation FROM public_profiles "
                "WHERE user_id = :uid"
            ),
            {"uid": str(user_id)},
        )
    ).first()
    base: dict[str, Any] = {
        "allowed_kinds": list(ALLOWED_PUBLIC_KINDS),
        "stats": await _stats(session, str(user_id)),
    }
    if row is None:
        return {
            **base,
            "configured": False,
            "enabled": False,
            "slug": None,
            "curation": TwinCuration().model_dump(),
        }
    curation = row.curation or {}
    return {
        **base,
        "configured": True,
        "enabled": row.enabled,
        "slug": row.slug,
        "curation": {
            "visible_kinds": visible_kinds(curation),
            "charter": curation.get("charter") or DEFAULT_CHARTER,
            "suggested_questions": curation.get("suggested_questions") or [],
        },
    }


@router.put("")
async def update_twin(
    body: TwinUpdate, user_id: CurrentUserId, session: SessionDep
) -> dict[str, Any]:
    import json

    from fastapi import HTTPException

    curation_json: str | None = None
    if body.curation is not None:
        cur = body.curation.model_dump()
        cur["visible_kinds"] = [
            k for k in cur["visible_kinds"] if k in ALLOWED_PUBLIC_KINDS
        ]
        curation_json = json.dumps(cur)

    if body.slug is not None and not validate_vanity_slug(body.slug):
        raise HTTPException(
            status_code=422,
            detail="Slug inválido: 4-40 caracteres, minúsculas/números/guiones.",
        )

    row = (
        await session.execute(
            text("SELECT slug FROM public_profiles WHERE user_id = :uid"),
            {"uid": str(user_id)},
        )
    ).first()
    if row is None:
        slug = body.slug or new_slug()
        await session.execute(
            text(
                "INSERT INTO public_profiles (user_id, slug, enabled, curation) "
                "VALUES (:uid, :slug, :enabled, CAST(:cur AS jsonb))"
            ),
            {
                "uid": str(user_id),
                "slug": slug,
                "enabled": bool(body.enabled),
                "cur": curation_json or "{}",
            },
        )
    else:
        sets, params = ["updated_at = now()"], {"uid": str(user_id)}
        if body.enabled is not None:
            sets.append("enabled = :enabled")
            params["enabled"] = body.enabled
        if body.slug is not None:
            sets.append("slug = :slug")
            params["slug"] = body.slug
        if curation_json is not None:
            sets.append("curation = CAST(:cur AS jsonb)")
            params["cur"] = curation_json
        try:
            await session.execute(
                text(f"UPDATE public_profiles SET {', '.join(sets)} WHERE user_id = :uid"),
                params,
            )
        except Exception as exc:
            if "unique" in str(exc).lower():
                raise HTTPException(status_code=409, detail="Ese slug ya está en uso.")
            raise
    # Read-back BEFORE commit: `SET LOCAL app.current_user_id` dies with the
    # transaction, so a post-commit SELECT runs GUC-less and RLS hides the
    # row (the documented RLS-flip bug class — returns slug=None).
    fresh = await get_twin(user_id, session)
    await session.commit()
    return fresh


@router.post("/slug")
async def regenerate_slug(user_id: CurrentUserId, session: SessionDep) -> dict[str, Any]:
    """New random slug — the old public URL stops resolving immediately."""
    slug = new_slug()
    await session.execute(
        text(
            "UPDATE public_profiles SET slug = :slug, updated_at = now() "
            "WHERE user_id = :uid"
        ),
        {"slug": slug, "uid": str(user_id)},
    )
    await session.commit()
    return {"slug": slug}
