"""Tools to introspect and steer the coherence engine.

When the agent isn't sure if something already exists, it can call
`find_existing` directly. When the user wants to fold two entries into one,
`propose_merge` opens a suggestion the user confirms via the chat UI.
`mark_stale` flags an entry as obsolete without deleting it.
"""
from __future__ import annotations

from typing import Any
from uuid import UUID, uuid4

from agno.run.base import RunContext
from agno.tools import tool
from sqlalchemy import text

from src.coherence.infrastructure.semantic_matcher import PgVectorSemanticMatcher
from src.shared.db import with_user_session


@tool(
    name="find_existing",
    description=(
        "Look up entries that semantically match a query in a given entity "
        "type. Use when the user says 'tengo X' and you want to know if it's "
        "already captured before proposing it again."
    ),
)
async def find_existing(
    run_context: RunContext,
    entity_type: str,
    query: str,
    threshold: float = 0.80,
) -> dict[str, Any]:
    user_id = run_context.user_id
    if not user_id:
        return {"ok": False, "error": "missing user_id"}
    async with with_user_session(UUID(user_id)) as session:
        matcher = PgVectorSemanticMatcher(session)
        hits = await matcher.find_most_similar(
            user_id=UUID(user_id),
            entity_type=entity_type,
            text=query,
            threshold=threshold,
            top_k=5,
        )
        return {"ok": True, "matches": hits}


@tool(
    name="propose_merge_suggestion",
    description=(
        "When you detect two existing entries that look like duplicates, "
        "open a suggestion so the user can confirm a merge. Pass the entity "
        "type and the list of candidate ids."
    ),
)
async def propose_merge_suggestion(
    run_context: RunContext,
    entity_type: str,
    candidate_ids: list[str],
    reason: str | None = None,
) -> dict[str, Any]:
    user_id = run_context.user_id
    if not user_id:
        return {"ok": False, "error": "missing user_id"}
    if len(candidate_ids) < 2:
        return {"ok": False, "error": "need at least 2 candidates"}
    async with with_user_session(UUID(user_id)) as session:
        sid = uuid4()
        import json

        payload = json.dumps(
            {
                "entity_type": entity_type,
                "candidates": candidate_ids,
                "reason": reason,
            }
        )
        await session.execute(
            text(
                """
                INSERT INTO suggestions
                    (id, user_id, kind, title, body, payload, source, status, priority, created_at)
                VALUES
                    (:id, :uid, 'merge_candidates', :title, NULL,
                     CAST(:payload AS jsonb), 'coherence_tool', 'pending', 60, now())
                """
            ),
            {
                "id": str(sid),
                "uid": user_id,
                "title": f"Posibles duplicados detectados ({entity_type})",
                "payload": payload,
            },
        )
        return {"ok": True, "suggestion_id": str(sid)}


@tool(
    name="list_pending_curation",
    description=(
        "List everything the curator has flagged for the user to confirm: "
        "duplicate-merge suggestions, outlier entities to review, and "
        "low-confidence ESCO links to pick. Use this during proactive "
        "maintenance check-ins to surface housekeeping the user can resolve "
        "in one go, instead of letting it pile up silently."
    ),
)
async def list_pending_curation(
    run_context: RunContext,
    limit: int = 10,
) -> dict[str, Any]:
    user_id = run_context.user_id
    if not user_id:
        return {"ok": False, "error": "missing user_id"}
    async with with_user_session(UUID(user_id)) as session:
        suggestions = (
            await session.execute(
                text(
                    """
                    SELECT id::text AS id, kind, title, priority
                    FROM suggestions
                    WHERE status = 'pending'
                    ORDER BY priority DESC, created_at DESC
                    LIMIT :lim
                    """
                ),
                {"lim": limit},
            )
        ).all()
        quarantine = (
            await session.execute(
                text(
                    """
                    SELECT id::text AS id, kind, reason, notes
                    FROM entity_quarantine
                    WHERE resolved_at IS NULL
                    ORDER BY created_at DESC
                    LIMIT :lim
                    """
                ),
                {"lim": limit},
            )
        ).all()
    return {
        "ok": True,
        "suggestions": [
            {"id": r.id, "kind": r.kind, "title": r.title, "priority": r.priority}
            for r in suggestions
        ],
        "quarantine": [
            {"id": r.id, "kind": r.kind, "reason": r.reason, "notes": r.notes}
            for r in quarantine
        ],
        "total": len(suggestions) + len(quarantine),
    }


@tool(
    name="mark_stale",
    description=(
        "Mark a universe entry as obsolete without deleting it. Sets "
        "confidence to 0.3 and emits a change_log row. Useful when the user "
        "says 'ya no uso X' o 'eso era de hace años'."
    ),
)
async def mark_stale(
    run_context: RunContext,
    entity_type: str,
    entity_id: str,
    reason: str | None = None,
) -> dict[str, Any]:
    from src.graph.domain.registry import GRAPH_REGISTRY

    user_id = run_context.user_id
    if not user_id:
        return {"ok": False, "error": "missing user_id"}
    # Iterate GRAPH_REGISTRY (single source of truth): every
    # supports_stale=True entity kind is automatically mark-stale-able.
    # Adding a new vertical adds one registry entry → mark_stale picks it
    # up for free.
    reg = GRAPH_REGISTRY.get(entity_type)
    if reg is None or not reg.supports_stale:
        return {"ok": False, "error": f"entity_type {entity_type!r} does not support stale"}
    async with with_user_session(UUID(user_id)) as session:
        table = reg.sql_table
        result = await session.execute(
            text(
                f"UPDATE {table} SET confidence = 0.3, updated_at = now() "  # noqa: S608
                f"WHERE id = :eid AND user_id = :uid "
                f"RETURNING id"
            ),
            {"eid": entity_id, "uid": user_id},
        )
        if result.first() is None:
            return {"ok": False, "error": "entity not found"}

        # Record in change_log
        import json

        await session.execute(
            text(
                """
                INSERT INTO universe_change_log (
                    id, user_id, entity_type, entity_id, change_type, field,
                    old_value, new_value, reason, source, agent_run_id, changed_at
                ) VALUES (
                    :id, :uid, :etype, :eid, 'update', 'confidence',
                    NULL, CAST(:nv AS jsonb), :reason, 'agent_chat', :run_id, now()
                )
                """
            ),
            {
                "id": str(uuid4()),
                "uid": user_id,
                "etype": entity_type,
                "eid": entity_id,
                "nv": json.dumps(0.3),
                "reason": reason or "marked stale by agent",
                "run_id": run_context.run_id,
            },
        )
        return {"ok": True, "entity_id": entity_id, "confidence": 0.3}


@tool(
    name="get_recent_activity",
    description=(
        "Summarise what changed in the user's universe recently — the "
        "chronological projection of the chat episodes. Answers '¿qué "
        "hicimos la semana pasada?' / 'what have we been working on?'. "
        "Returns recent create/update/delete events with entity type, "
        "reason and timestamp, plus per-type counts."
    ),
)
async def get_recent_activity(
    run_context: RunContext,
    days: int = 7,
    limit: int = 25,
) -> dict[str, Any]:
    user_id = run_context.user_id
    if not user_id:
        return {"ok": False, "error": "missing user_id"}
    days = max(1, min(days, 90))
    async with with_user_session(UUID(user_id)) as session:
        rows = (
            await session.execute(
                text(
                    """
                    SELECT entity_type, change_type, reason, changed_at
                    FROM universe_change_log
                    WHERE changed_at > now() - make_interval(days => :days)
                    ORDER BY changed_at DESC
                    LIMIT :lim
                    """
                ),
                {"days": days, "lim": limit},
            )
        ).all()
        counts = (
            await session.execute(
                text(
                    """
                    SELECT entity_type, change_type, count(*) AS n
                    FROM universe_change_log
                    WHERE changed_at > now() - make_interval(days => :days)
                    GROUP BY entity_type, change_type
                    ORDER BY n DESC
                    """
                ),
                {"days": days},
            )
        ).all()
    return {
        "ok": True,
        "days": days,
        "events": [
            {
                "entity_type": r.entity_type,
                "change_type": r.change_type,
                "reason": r.reason,
                "changed_at": r.changed_at.isoformat() if r.changed_at else None,
            }
            for r in rows
        ],
        "counts": [
            {"entity_type": r.entity_type, "change_type": r.change_type, "n": r.n}
            for r in counts
        ],
    }


@tool(
    name="get_change_history",
    description=(
        "Get the chronological history of changes for one entity. Useful when "
        "the user asks 'cuándo subí Python a expert' or 'cuándo dejé tal "
        "trabajo'."
    ),
)
async def get_change_history(
    run_context: RunContext,
    entity_type: str,
    entity_id: str,
    limit: int = 10,
) -> dict[str, Any]:
    user_id = run_context.user_id
    if not user_id:
        return {"ok": False, "error": "missing user_id"}
    async with with_user_session(UUID(user_id)) as session:
        from src.coherence.infrastructure.change_log_repo import (
            SqlAlchemyChangeLogRepository,
        )

        repo = SqlAlchemyChangeLogRepository(session)
        rows = await repo.list_for_entity(
            user_id=UUID(user_id),
            entity_type=entity_type,
            entity_id=UUID(entity_id),
            limit=limit,
        )
        return {"ok": True, "count": len(rows), "changes": rows}
