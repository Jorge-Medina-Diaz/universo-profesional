"""Nudges API (P3.A): the frontend's window into the proactive loop.

GET  /api/v1/nudges/active      → pending/surfaced nudges (marks them surfaced)
POST /api/v1/nudges/{id}/ack    → user acted on / dismissed a nudge
"""
from __future__ import annotations

from typing import Any, Literal
from uuid import UUID

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import text

from src.identity.interfaces.api.deps import CurrentUserId, SessionDep

router = APIRouter()


class Nudge(BaseModel):
    id: str
    kind: str
    payload: dict[str, Any]
    created_at: str


class NudgeList(BaseModel):
    nudges: list[Nudge]


class AckBody(BaseModel):
    action: Literal["acted", "dismissed"]


@router.get("/active", response_model=NudgeList)
async def active_nudges(user_id: CurrentUserId, session: SessionDep) -> NudgeList:
    rows = (
        await session.execute(
            text(
                "SELECT id, kind, payload, created_at FROM nudges "
                "WHERE user_id = :uid AND status IN ('pending','surfaced') "
                "ORDER BY created_at DESC LIMIT 5"
            ),
            {"uid": str(user_id)},
        )
    ).all()
    if rows:
        await session.execute(
            text(
                "UPDATE nudges SET status = 'surfaced', surfaced_at = now() "
                "WHERE id = ANY(:ids) AND status = 'pending'"
            ),
            {"ids": [r.id for r in rows]},
        )
        await session.commit()
    return NudgeList(
        nudges=[
            Nudge(
                id=str(r.id),
                kind=r.kind,
                payload=r.payload or {},
                created_at=r.created_at.isoformat(),
            )
            for r in rows
        ]
    )


@router.post("/{nudge_id}/ack")
async def ack_nudge(
    nudge_id: UUID, body: AckBody, user_id: CurrentUserId, session: SessionDep
) -> dict[str, str]:
    result = await session.execute(
        text(
            "UPDATE nudges SET status = :action, acted_at = now() "
            "WHERE id = :id AND user_id = :uid AND status IN ('pending','surfaced')"
        ),
        {"action": body.action, "id": str(nudge_id), "uid": str(user_id)},
    )
    if not result.rowcount:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="not_found")
    await session.commit()
    kind = (
        await session.execute(
            text("SELECT kind FROM nudges WHERE id = :id"), {"id": str(nudge_id)}
        )
    ).scalar()
    from src.shared.metrics import nudge_acted_total

    nudge_acted_total.labels(kind=kind or "unknown", action=body.action).inc()
    return {"status": body.action}
