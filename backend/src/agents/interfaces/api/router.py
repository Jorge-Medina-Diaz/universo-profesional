"""Agent management API — intent routing, context provider inspection.

These endpoints are NOT part of the AG-UI chat stream; they serve the
frontend's auxiliary UI (showing which agent mode is active, letting the
user inspect learned rules, etc.).
"""
from __future__ import annotations

import asyncio
import json
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

import asyncpg
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse
from jose import JWTError
from pydantic import BaseModel
from sqlalchemy import text
from src.agents.context_providers import IntentRouter
from src.agents.domain.intents import INTENT_GENERAL_CHAT
from src.agents.domain.sources import SOURCE_AGENT_CHAT
from src.agents.infrastructure.proposal_store import delete_proposal, get_proposal
from src.agents.memory.self_learning import SelfLearningEngine, UserFeedback
from src.coherence.application.upsert_use_cases import UpsertUniverseEntity
from src.coherence.infrastructure.change_log_repo import (
    SqlAlchemyChangeLogRepository,
)
from src.coherence.infrastructure.semantic_matcher import (
    PgVectorSemanticMatcher,
)
from src.identity.interfaces.api.deps import CurrentUserId, SessionDep
from src.shared.config import get_settings
from src.shared.db import with_user_session
from src.shared.errors import UnauthorizedError
from src.shared.listener import PgListener
from src.shared.metrics import (
    agent_proposals_confirmed_total,
    agent_proposals_rejected_total,
    agent_proposals_total,
)
from src.shared.security import decode_jwt
from src.shared.serialization import jsonify
from src.shared.uow import unit_of_work
from src.universe.application.discovery_service import DiscoveryProgressService

router = APIRouter()


# ---------------------------------------------------------------------------
# Proposal resolution — HITL confirm/edit/reject backend for proposal cards
# ---------------------------------------------------------------------------


class ResolveProposalBody(BaseModel):
    action: str  # "confirm" | "reject" | "modify"
    modified_data: dict[str, Any] | None = None


class ResolveProposalResponse(BaseModel):
    status: str
    entity_id: str | None = None
    diffs: list[dict[str, Any]] = []
    reason: str | None = None


@router.post("/proposals/{proposal_id}/resolve", response_model=ResolveProposalResponse)
async def resolve_proposal(
    proposal_id: str,
    body: ResolveProposalBody,
    user_id: CurrentUserId,
    session: SessionDep,
) -> ResolveProposalResponse:
    """Resolve a pending HITL proposal.

    On *confirm*: runs the entity through the coherence engine (same path as
    ``POST /api/v1/coherence/upsert``) and returns the outcome.
    On *reject*: records negative feedback in the self-learning loop.
    On *modify*: merges user edits into the stored payload, then upserts.
    """
    proposal = await get_proposal(str(user_id), proposal_id)
    if proposal is None:
        raise HTTPException(status_code=404, detail="Proposal not found or expired")

    if body.action not in ("confirm", "reject", "modify"):
        raise HTTPException(status_code=400, detail="Invalid action")

    entity_type: str = proposal["entity_type"]
    entity_data: dict[str, Any] = dict(proposal["entity_data"])

    agent_proposals_total.labels(entity_type=entity_type, action=body.action).inc()

    if body.action == "reject":
        engine = SelfLearningEngine(session)
        feedback = UserFeedback(
            user_id=UUID(str(user_id)),
            session_id=proposal.get("thread_id", ""),
            scope="proposal_rejection",
            trigger_message="",
            agent_action=f"propose_{entity_type}",
            user_expectation="",
            sentiment="negative",
            correction_detail=None,
        )
        await engine.record(feedback)
        await session.commit()
        await delete_proposal(str(user_id), proposal_id)
        agent_proposals_rejected_total.labels(entity_type=entity_type).inc()
        return ResolveProposalResponse(status="rejected", reason="Rejected by user")

    # confirm or modify
    if body.action == "modify" and body.modified_data:
        entity_data.update(body.modified_data)

    change_log = SqlAlchemyChangeLogRepository(session)
    matcher = PgVectorSemanticMatcher(session)
    uc = UpsertUniverseEntity(
        session, change_log=change_log, semantic_matcher=matcher
    )

    async with unit_of_work(session) as uow:
        outcome = await uc.execute(
            entity_type=entity_type,
            user_id=user_id,
            payload=entity_data,
            uow=uow,
            source=SOURCE_AGENT_CHAT,
            chat_session_id=proposal.get("thread_id"),
        )
        await uow.commit()

    await delete_proposal(str(user_id), proposal_id)
    agent_proposals_confirmed_total.labels(entity_type=entity_type).inc()

    return ResolveProposalResponse(
        status=outcome.status.value,
        entity_id=str(outcome.entity_id) if outcome.entity_id else None,
        diffs=[
            {"field": d.field, "old": jsonify(d.old), "new": jsonify(d.new)}
            for d in outcome.diffs
        ],
        reason=outcome.reason,
    )


@router.post("/route")
async def classify_intent(
    user_id: CurrentUserId,
    session: SessionDep,
    body: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Classify a user message and return the selected provider + memory context.

    This is a synchronous (non-streaming) endpoint used by the frontend to
    show the user which "mode" the agent is in before the chat stream starts.
    """
    if body is None:
        body = {}
    message = body.get("message", "")
    if not message:
        return {"intent": INTENT_GENERAL_CHAT, "provider": "universe_curator", "confidence": 0.0}

    router = IntentRouter(session, UUID(user_id))
    intent = await router.classify(message)
    provider = await router.get_provider(intent)
    memory_ctx = await provider.get_memory_context()

    return {
        "intent": intent.name,
        "provider": intent.provider_name,
        "confidence": intent.confidence,
        "memory_context": memory_ctx,
        "tools_available": [getattr(t, "__name__", str(t)) for t in provider.get_tools()],
    }


@router.get("/memory/rules")
async def list_learned_rules(
    user_id: CurrentUserId,
    session: SessionDep,
    scope: str | None = None,
) -> list[dict[str, Any]]:
    """Return the user's active procedural memory rules."""
    sql = """
        SELECT scope, trigger_pattern, action_rule, success_rate, hit_count, updated_at
        FROM user_procedural_memory
        WHERE user_id = :uid AND active = true
    """
    params: dict[str, Any] = {"uid": str(user_id)}
    if scope:
        sql += " AND scope = :scope"
        params["scope"] = scope
    sql += " ORDER BY success_rate DESC, hit_count DESC LIMIT 50"

    rows = (await session.execute(text(sql), params)).mappings().all()
    return [dict(r) for r in rows]


@router.get("/memory/facts")
async def list_semantic_facts(
    user_id: CurrentUserId,
    session: SessionDep,
    category: str | None = None,
) -> list[dict[str, Any]]:
    """Return the user's semantic memory (facts)."""
    sql = """
        SELECT category, key, value, confidence, source, updated_at
        FROM user_semantic_memory
        WHERE user_id = :uid
    """
    params: dict[str, Any] = {"uid": str(user_id)}
    if category:
        sql += " AND category = :cat"
        params["cat"] = category
    sql += " ORDER BY confidence DESC, updated_at DESC LIMIT 50"

    rows = (await session.execute(text(sql), params)).mappings().all()
    return [dict(r) for r in rows]


@router.post("/feedback")
async def record_user_feedback(
    user_id: CurrentUserId,
    session: SessionDep,
    body: dict[str, Any] | None = None,
) -> dict[str, str]:
    """Record explicit user feedback (thumbs up/down, rejection, correction).

    Called by the frontend when a user rejects a HITL proposal, edits a
    suggested entity, or gives explicit feedback on an agent action.
    """
    if body is None:
        body = {}
    engine = SelfLearningEngine(session)
    feedback = UserFeedback(
        user_id=UUID(str(user_id)),
        session_id=body.get("session_id", ""),
        scope=body.get("scope", "universe_updates"),
        trigger_message=body.get("trigger_message", ""),
        agent_action=body.get("agent_action", ""),
        user_expectation=body.get("user_expectation", ""),
        sentiment=body.get("sentiment", "neutral"),
        correction_detail=body.get("correction_detail"),
    )
    await engine.record(feedback)
    await session.commit()
    return {"status": "recorded"}


@router.get("/discovery/progress")
async def get_discovery_progress(
    user_id: CurrentUserId,
    session: SessionDep,
) -> dict[str, Any]:
    """Return the user's discovery progress — a living view of their growing profile.

    This endpoint gives the frontend real-time visibility into how the user's
    professional universe is expanding through conversation, import, and manual
    entry. It powers progress indicators, discovery dashboards, and "universe
    vitality" widgets.
    """
    svc = DiscoveryProgressService(session)
    return await svc.get_progress(UUID(str(user_id)))


@router.get("/discovery/stream")
async def discovery_progress_stream(request: Request) -> StreamingResponse:
    """SSE endpoint for real-time discovery progress updates.

    Emits a JSON event every time a new row is inserted into
    ``universe_change_log`` for the authenticated user.  Keeps the
    connection alive with heartbeat comments.
    """
    user_id = _extract_user_id_from_request(request)
    uid = UUID(user_id)

    async def event_generator() -> Any:
        last_seen_at: datetime | None = datetime.now(UTC)
        heartbeat_due = datetime.now(UTC)
        poll_interval = 3.0  # seconds
        heartbeat_interval = 15.0  # seconds

        settings = get_settings()
        dsn = settings.database_url.replace("postgresql+asyncpg://", "postgresql://", 1)

        listener = None
        conn = None
        try:
            try:
                conn = await asyncpg.connect(dsn)
                listener = PgListener(conn)
            except Exception:
                # Fallback: if LISTEN/NOTIFY fails, pure polling continues below.
                listener = None

            while True:
                now = datetime.now(UTC)

                # Graceful disconnect — stop polling and release the generator.
                if await request.is_disconnected():
                    break

                # Heartbeat comment to keep proxies / load balancers happy.
                if now >= heartbeat_due:
                    yield ":heartbeat\n\n"
                    heartbeat_due = now + timedelta(seconds=heartbeat_interval)

                # Wait for a notification (event-driven wakeup) or timeout.
                notify_payload: str | None = None
                if listener is not None:
                    notify_payload = await listener.get(wait_for=poll_interval)
                else:
                    await asyncio.sleep(poll_interval)

                # If a notification arrived for a different user, skip the DB round-trip.
                if notify_payload is not None and notify_payload != str(uid):
                    continue

                # Poll DB for new change-log rows using a fresh short-lived session.
                new_rows: list[dict[str, Any]] = []
                async with with_user_session(uid) as session:
                    sql = """
                        SELECT entity_type, change_type, source, new_value, changed_at
                        FROM universe_change_log
                        WHERE user_id = :uid
                    """
                    params: dict[str, Any] = {"uid": str(uid)}
                    if last_seen_at is not None:
                        sql += " AND changed_at > :since"
                        params["since"] = last_seen_at
                    sql += " ORDER BY changed_at ASC"
                    rows = (await session.execute(text(sql), params)).mappings().all()
                    new_rows = [dict(r) for r in rows]

                if new_rows:
                    # Advance watermark to the newest row so the next poll is idempotent.
                    last_seen_at = max(
                        r["changed_at"] for r in new_rows if r.get("changed_at")
                    )
                    for row in new_rows:
                        payload = {
                            "type": "entity_discovered",
                            "entity_type": row["entity_type"],
                            "name": _extract_entity_name(row.get("new_value")),
                            "source": row["source"],
                        }
                        yield f"data: {json.dumps(payload)}\n\n"
        finally:
            if conn is not None:
                await conn.close()

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


def _extract_user_id_from_request(request: Request) -> str:
    """Decode the Bearer JWT from the request headers (no DB session required)."""
    auth = request.headers.get("authorization", "")
    if not auth.lower().startswith("bearer "):
        raise UnauthorizedError("Missing bearer token")
    token = auth.split(" ", 1)[1].strip()
    try:
        claims = decode_jwt(token, audience="cvs-saas-api")
    except JWTError as exc:
        raise UnauthorizedError(f"Invalid token: {exc}") from exc
    uid = claims.get("sub")
    if not uid:
        raise UnauthorizedError("Token missing sub")
    return str(uid)


def _extract_entity_name(new_value: Any) -> str:
    """Best-effort extraction of a human-readable name from a change-log JSONB value."""
    if not isinstance(new_value, dict):
        return "Unknown"
    for key in ("name", "title", "label", "headline", "company", "institution"):
        val = new_value.get(key)
        if isinstance(val, str) and val.strip():
            return val.strip()
    return "Unknown"
