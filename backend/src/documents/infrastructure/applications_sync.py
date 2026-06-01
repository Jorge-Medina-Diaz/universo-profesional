"""Applications aggregate sync + reads (F).

The Kanban tracker still writes jobs.description_parsed._tracker (the FE talks to
/jobs). This mirrors each mutation into the typed `applications` table so the
aggregate stays live + canonical, and exposes a typed read for new clients / the
future Kanban cutover. Lives in infrastructure (called by the jobs router on
each write). Atomic upsert keyed on the unique (user_id, job_id).
"""
from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import select, text
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from src.documents.infrastructure.orm import ApplicationOrm
from src.shared.security import utc_now

# tracker status (FE/_tracker vocabulary) -> typed pipeline stage
_STATUS_TO_STAGE = {
    "interested": "saved",
    "applied": "applied",
    "interviewing": "interview",
    "offer": "offer",
    "rejected": "closed",
    "archived": "closed",
}
_STAGE_TS = {
    "applied": "applied_at",
    "screen": "screen_at",
    "interview": "interview_at",
    "offer": "offer_at",
    "closed": "closed_at",
}


def _parse_dt(value: Any) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None


async def upsert_application_from_tracker(
    session: AsyncSession,
    *,
    user_id: UUID,
    job_id: UUID,
    tracker: dict[str, Any],
    document_id: UUID | None = None,
) -> None:
    """Mirror a job's _tracker blob into the typed applications row."""
    now = utc_now()
    status = tracker.get("status") or "interested"
    stage = _STATUS_TO_STAGE.get(status, "saved")
    position = tracker.get("position")
    match_score = tracker.get("match_score")
    base: dict[str, Any] = {
        "stage": stage,
        "status": status,
        "position": float(position) if position is not None else None,
        "notes": tracker.get("notes"),
        "next_action_at": _parse_dt(tracker.get("next_action_at")),
        "applied_at": _parse_dt(tracker.get("applied_at")),
        "match_score": int(match_score) if match_score is not None else None,
        "match": tracker.get("match"),
        "closed_reason": status if status in ("rejected", "archived") else None,
        "updated_at": now,
    }
    ts_col = _STAGE_TS.get(stage)
    if ts_col and ts_col != "applied_at":
        base[ts_col] = now  # stamp the stage's timestamp on transition
    values = {
        "id": uuid4(),
        "user_id": user_id,
        "job_id": job_id,
        "document_id": document_id,
        "created_at": now,
        "contacts": [],
        **base,
    }
    stmt = (
        pg_insert(ApplicationOrm)
        .values(**values)
        # uq_applications_user_job is a PARTIAL unique index (WHERE job_id IS
        # NOT NULL), not a named constraint — infer it by elements + predicate.
        .on_conflict_do_update(
            index_elements=["user_id", "job_id"],
            index_where=text("job_id IS NOT NULL"),
            set_=base,
        )
    )
    await session.execute(stmt)


async def list_applications(session: AsyncSession, user_id: UUID) -> list[dict[str, Any]]:
    """Typed pipeline rows, positioned-first then by position."""
    rows = (
        (
            await session.execute(
                select(ApplicationOrm)
                .where(ApplicationOrm.user_id == user_id)
                .order_by(ApplicationOrm.position.is_(None), ApplicationOrm.position)
            )
        )
        .scalars()
        .all()
    )
    return [
        {
            "id": str(a.id),
            "job_id": str(a.job_id) if a.job_id else None,
            "document_id": str(a.document_id) if a.document_id else None,
            "stage": a.stage,
            "status": a.status,
            "position": a.position,
            "notes": a.notes,
            "next_action_at": a.next_action_at.isoformat() if a.next_action_at else None,
            "applied_at": a.applied_at.isoformat() if a.applied_at else None,
            "interview_at": a.interview_at.isoformat() if a.interview_at else None,
            "offer_at": a.offer_at.isoformat() if a.offer_at else None,
            "closed_at": a.closed_at.isoformat() if a.closed_at else None,
            "closed_reason": a.closed_reason,
            "match_score": a.match_score,
            "match": a.match,
            "contacts": a.contacts or [],
        }
        for a in rows
    ]
