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
        )
        await uow.commit()
    return UpsertResponse(
        status=outcome.status.value,
        entity_id=str(outcome.entity_id) if outcome.entity_id else None,
        diffs=[
            {"field": d.field, "old": _jsonify(d.old), "new": _jsonify(d.new)}
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
) -> list[dict[str, Any]]:
    repo = SqlAlchemyChangeLogRepository(session)
    if entity_type and entity_id:
        from uuid import UUID

        return await repo.list_for_entity(
            user_id=UUID(user_id),
            entity_type=entity_type,
            entity_id=UUID(entity_id),
            limit=limit,
        )
    from uuid import UUID

    return await repo.list_for_user(user_id=UUID(user_id), limit=limit)


def _jsonify(v: Any) -> Any:
    from datetime import date, datetime
    from uuid import UUID

    if isinstance(v, (datetime, date)):
        return v.isoformat()
    if isinstance(v, UUID):
        return str(v)
    if isinstance(v, list):
        return [_jsonify(x) for x in v]
    return v
