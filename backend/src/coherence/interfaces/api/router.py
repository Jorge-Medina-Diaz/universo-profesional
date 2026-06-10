"""Coherence REST API.

`POST /api/v1/coherence/upsert` runs an entity upsert through the same engine
the agent uses. The frontend's confirmation cards (DiffCard, EntryCard) post
here instead of `universe.add` so EVERY write — whether from chat, REST, or
import — goes through merge rules and emits a change_log row.

`GET /api/v1/coherence/changes` exposes the chronological feed for the UI
"Trayectoria" tab.
"""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Query
from pydantic import BaseModel, Field

from src.coherence.application.upsert_use_cases import UpsertUniverseEntity
from src.coherence.infrastructure.change_log_repo import (
    SqlAlchemyChangeLogRepository,
)
from src.coherence.infrastructure.semantic_matcher import (
    PgVectorSemanticMatcher,
)
from src.identity.interfaces.api.deps import CurrentUserId, SessionDep
from src.shared.serialization import jsonify
from src.shared.uow import unit_of_work

router = APIRouter()


class UpsertBody(BaseModel):
    entity_type: str
    payload: dict[str, Any]
    source: str = Field("manual", description="Origin tag (agent_chat, manual, import_*).")
    chat_session_id: str | None = Field(
        None,
        description=(
            "Chat session id (Sprint P). When present, the entity is linked "
            "to the corresponding Episode vertex via :TOUCHED_IN."
        ),
    )
    op_hint: str | None = Field(
        None,
        description=(
            "Mem0-style write contract (Sprint P). One of 'ADD', 'UPDATE', "
            "'DELETE', 'NOOP'. When omitted, the coherence engine decides "
            "(legacy semantics). When the agent supplies a hint, it pins the "
            "execution path so behavior matches the agent's stated intent."
        ),
    )
    entity_id: str | None = Field(
        None,
        description=(
            "Target a SPECIFIC entity (manual edit from the universe inspector). "
            "When present, the engine skips name/semantic matching and updates "
            "exactly this entity through the merge path — so a manual edit gets "
            "the same coherence change_log + graph mirror as an agent edit, "
            "without rename-duplicate risk."
        ),
    )


class UpsertResponse(BaseModel):
    status: str
    entity_id: str | None
    diffs: list[dict[str, Any]]
    suggestion_id: str | None = None
    reason: str | None = None


@router.post("/upsert", response_model=UpsertResponse)
async def upsert(
    body: UpsertBody, user_id: CurrentUserId, session: SessionDep
) -> UpsertResponse:
    change_log = SqlAlchemyChangeLogRepository(session)
    matcher = PgVectorSemanticMatcher(session)
    uc = UpsertUniverseEntity(session, change_log=change_log, semantic_matcher=matcher)
    async with unit_of_work(session) as uow:
        outcome = await uc.execute(
            entity_type=body.entity_type,
            user_id=user_id,
            payload=body.payload,
            uow=uow,
            source=body.source,
            chat_session_id=body.chat_session_id,
            op_hint=body.op_hint,
            entity_id=body.entity_id,
        )
        await uow.commit()
    return UpsertResponse(
        status=outcome.status.value,
        entity_id=str(outcome.entity_id) if outcome.entity_id else None,
        diffs=[
            {"field": d.field, "old": jsonify(d.old), "new": jsonify(d.new)}
            for d in outcome.diffs
        ],
        suggestion_id=str(outcome.suggestion_id) if outcome.suggestion_id else None,
        reason=outcome.reason,
    )


@router.get("/changes")
async def list_changes(
    user_id: CurrentUserId,
    session: SessionDep,
    limit: int = Query(50, ge=1, le=200),
    entity_type: str | None = Query(None),
    entity_id: str | None = Query(None),
    cursor: str | None = Query(None),
) -> dict[str, Any]:
    """Keyset-paginated change feed: ``{items, next_cursor}``. The single-entity
    history (entity_type+entity_id) is bounded and returned in the same envelope
    with next_cursor=null."""
    from uuid import UUID

    repo = SqlAlchemyChangeLogRepository(session)
    if entity_type and entity_id:
        items = await repo.list_for_entity(
            user_id=UUID(user_id),
            entity_type=entity_type,
            entity_id=UUID(entity_id),
            limit=limit,
        )
        return {"items": items, "next_cursor": None}
    return await repo.list_for_user(user_id=UUID(user_id), limit=limit, cursor=cursor)

class ReviewItem(BaseModel):
    id: str
    source: str  # 'suggestion' | 'quarantine'
    kind: str | None = None
    title: str
    detail: str | None = None
    created_at: str | None = None


class ReviewQueue(BaseModel):
    items: list[ReviewItem]
    total: int


@router.get("/review-queue", response_model=ReviewQueue)
async def review_queue(
    user_id: CurrentUserId,
    session: SessionDep,
    limit: int = Query(20, ge=1, le=50),
) -> ReviewQueue:
    """Everything waiting for the user's judgement, in ONE list (P3.E):
    pending suggestions + unresolved ESCO/dedup quarantine. Items resolve
    through their existing flows (chat cards / suggestions surface) — this
    endpoint only aggregates, so there is exactly one inbox to drain."""
    from sqlalchemy import text

    sugg = (
        await session.execute(
            text(
                "SELECT id::text AS id, kind, title, body, created_at "
                "FROM suggestions WHERE status = 'pending' AND user_id = :uid "
                "ORDER BY priority DESC, created_at DESC LIMIT :lim"
            ),
            {"lim": limit, "uid": user_id},
        )
    ).all()
    quar = (
        await session.execute(
            text(
                "SELECT id::text AS id, kind, reason, notes, created_at "
                "FROM entity_quarantine WHERE resolved_at IS NULL AND user_id = :uid "
                "ORDER BY created_at DESC LIMIT :lim"
            ),
            {"lim": limit, "uid": user_id},
        )
    ).all()
    items = [
        ReviewItem(
            id=r.id,
            source="suggestion",
            kind=r.kind,
            title=str(r.title or "Sugerencia"),
            detail=(str(r.body)[:200] if r.body else None),
            created_at=r.created_at.isoformat() if r.created_at else None,
        )
        for r in sugg
    ] + [
        ReviewItem(
            id=r.id,
            source="quarantine",
            kind=r.kind,
            title=str(r.reason or "Revision pendiente"),
            detail=(str(r.notes)[:200] if r.notes else None),
            created_at=r.created_at.isoformat() if r.created_at else None,
        )
        for r in quar
    ]
    items.sort(key=lambda i: i.created_at or "", reverse=True)
    return ReviewQueue(items=items[:limit], total=len(items))

