"""Post-run fire-and-forget tasks for AG-UI endpoints."""
from __future__ import annotations

import asyncio
from uuid import UUID

import structlog
from sqlalchemy import text

from src.agents.domain.sources import SOURCE_AGENT_CHAT
from src.agents.workflows.universe_enrichment import UniverseEnrichmentEngine
from src.llm_tracking.application.tracker import log_agno_run
from src.llm_tracking.infrastructure.repository import SqlalchemyLlmUsageLogRepository
from src.shared.db import with_user_session

logger = structlog.get_logger(__name__)

# Per-user serialization of fire-and-forget enrichment. Each SSE turn spawns a
# task, and the conversation window OVERLAPS the previous turn — so without a
# lock, turn N+1 re-extracts turn N's content while N is still mid-run and the
# semantic dedup (which only sees committed rows) lets BOTH create the same
# entity. Serializing per user makes N+1 wait for N to commit, so the dedup
# sees it. (Single-process deployment; a multi-replica setup would add a
# Postgres advisory lock for cross-process serialization.)
_enrich_locks: dict[str, asyncio.Lock] = {}


def _user_enrich_lock(user_id: str) -> asyncio.Lock:
    lock = _enrich_locks.get(user_id)
    if lock is None:
        lock = asyncio.Lock()
        _enrich_locks[user_id] = lock
    return lock


async def _enrich_universe_from_chat(
    user_id: str,
    text: str,
    thread_id: str,
) -> None:
    """Run the Universe Enrichment Engine on a user message.

    This is fire-and-forget from the SSE stream; failures are logged but never
    propagated to the client.
    """
    try:
        uid = UUID(user_id)
        async with _user_enrich_lock(user_id):
            async with with_user_session(uid) as session:
                engine = UniverseEnrichmentEngine(session, uid)
                result = await engine.process(text, source=SOURCE_AGENT_CHAT)
            logger.info(
                "chat_universe_enriched",
                user_id=user_id,
                thread_id=thread_id,
                entities_created=result.entities_created,
                entities_merged=result.entities_merged,
                relations_created=result.relations_created,
                errors=len(result.errors),
            )
    except Exception as exc:
        logger.warning("chat_universe_enrichment_failed", error=str(exc), user_id=user_id)


async def _persist_agno_usage(session_id: str, user_id: str) -> None:
    """Query ai.agno_sessions and persist usage metrics into llm_usage_logs.

    Called fire-and-forget from the streaming finally block so it never
    blocks the SSE connection.
    """
    try:
        uid = UUID(user_id)
        async with with_user_session(uid) as session:
            # Agno stores each turn as a run inside ai.agno_sessions.runs (JSONB).
            # We grab the latest run for this session.
            result = await session.execute(
                text(
                    """
                    SELECT runs
                    FROM ai.agno_sessions
                    WHERE session_id = :sid
                    ORDER BY updated_at DESC
                    LIMIT 1
                    """
                ),
                {"sid": session_id},
            )
            row = result.fetchone()
            if not row or not row.runs:
                return
            runs = row.runs
            if not isinstance(runs, list) or len(runs) == 0:
                return
            last_run = runs[-1]
            metrics = last_run.get("metrics") or {}
            run_id = last_run.get("run_id")
            await log_agno_run(
                SqlalchemyLlmUsageLogRepository(session),
                user_id=uid,
                run_id=run_id,
                session_id=session_id,
                metrics=metrics,
                agent="universe_coordinator",
            )
            await session.commit()
    except Exception as exc:
        logger.warning("persist_agno_usage_failed", error=str(exc))
