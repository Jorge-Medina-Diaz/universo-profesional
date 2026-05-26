"""Shape REST API — /api/v1/universe/shape

Exposes the polyglot shape (area_strengths + primary/secondary + shape_type)
to the frontend tech_radar widget and to the React UI in general.

The shape is cached on `universes.primary_area` + `area_strengths`; if it's
stale (computed_at older than `STALE_DAYS`) we recompute on-the-fly.
"""
from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from fastapi import APIRouter, Query

from src.identity.interfaces.api.deps import CurrentUserId, SessionDep
from src.universe.application.shape_service import (
    compute_area_strengths,
    load_area_strengths,
)

router = APIRouter()

STALE_DAYS = 7


def _shape_type(strengths: list[Any], primary_areas: list[str]) -> str:
    from src.universe.application.shape_service import _infer_shape

    scores = {s.area: s.confidence for s in strengths}
    return _infer_shape(scores, primary_areas)


@router.get("")
async def get_shape(
    user_id: CurrentUserId,
    session: SessionDep,
    force: bool = Query(default=False, description="Force recompute"),
) -> dict[str, Any]:
    strengths, primary, secondary_areas = await load_area_strengths(session, user_id)
    now = datetime.now(UTC)
    is_stale = True
    computed_at: datetime | None = None
    if strengths:
        computed_at = max(s.computed_at for s in strengths)
        is_stale = (now - computed_at) > timedelta(days=STALE_DAYS)
    if force or not strengths or is_stale:
        result = await compute_area_strengths(session, user_id)
        await session.commit()
        strengths = result.strengths
        primary = result.primary_areas[0] if result.primary_areas else None
        secondary_areas = result.secondary_areas
        computed_at = result.computed_at
        is_stale = False

    primary_areas = [s.area for s in strengths if s.is_primary]
    shape_type = _shape_type(strengths, primary_areas)

    return {
        "ok": True,
        "shape_type": shape_type,
        "primary_area": primary,
        "primary_areas": primary_areas,
        "secondary_areas": secondary_areas,
        "computed_at": computed_at.isoformat() if computed_at else None,
        "is_stale": is_stale,
        "strengths": [
            {
                "area": s.area,
                "depth_years": float(s.depth_years),
                "breadth_count": s.breadth_count,
                "recency_months": s.recency_months,
                "confidence": float(s.confidence),
                "is_primary": s.is_primary,
            }
            for s in sorted(strengths, key=lambda x: x.confidence, reverse=True)
        ],
    }


@router.post("/recompute")
async def recompute_shape(
    user_id: CurrentUserId,
    session: SessionDep,
) -> dict[str, Any]:
    result = await compute_area_strengths(session, user_id)
    await session.commit()
    return {
        "ok": True,
        "shape_type": result.shape_type,
        "primary_areas": result.primary_areas,
        "secondary_areas": result.secondary_areas,
        "computed_at": result.computed_at.isoformat(),
        "strengths_count": len(result.strengths),
    }


@router.get("/signals")
async def list_signals(
    user_id: CurrentUserId,
    session: SessionDep,
    sector: str | None = Query(default=None),
    status: str | None = Query(default=None),
) -> dict[str, Any]:
    from src.universe.application.signal_extraction import list_user_signals_with_chunk

    rows = await list_user_signals_with_chunk(
        session, user_id, sector=sector, status=status
    )
    by_status: dict[str, int] = {}
    for r in rows:
        s = r.get("status") or "unknown"
        by_status[s] = by_status.get(s, 0) + 1
    return {
        "ok": True,
        "total": len(rows),
        "sector": sector,
        "status": status,
        "by_status": by_status,
        "signals": [
            {
                "id": str(r["signal_id"]),
                "rubric_slug": r.get("rubric_slug"),
                "sector": r.get("sector"),
                "section_kind": r.get("section_kind"),
                "heading": r.get("heading"),
                "status": r.get("status"),
                "confidence": float(r.get("confidence", 0)),
                "evidence_count": len(r.get("evidence_entity_ids") or []),
            }
            for r in rows
        ],
    }


@router.post("/signals/recompute")
async def recompute_signals(
    user_id: CurrentUserId,
    session: SessionDep,
    sector: str | None = Query(default=None),
) -> dict[str, Any]:
    from src.universe.application.signal_extraction import extract_user_signals

    result = await extract_user_signals(session, user_id, sector=sector)
    await session.commit()
    return {
        "ok": True,
        "sector": sector,
        "created": result.signals_created,
        "updated": result.signals_updated,
        "removed": result.signals_removed,
        "by_status": result.by_status,
    }
