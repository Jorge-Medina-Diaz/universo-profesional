"""Arq-backed scheduler that enqueues embedding-refresh jobs."""
from __future__ import annotations

from uuid import UUID

import structlog
from arq import create_pool
from arq.connections import RedisSettings

from src.shared.config import get_settings
from src.universe.application.ports import EmbeddingRefreshScheduler

logger = structlog.get_logger(__name__)


class ArqEmbeddingScheduler(EmbeddingRefreshScheduler):
    """Enqueue embedding refresh task on Redis.

    In-process fallback: if the queue is unreachable, we run the embedding
    synchronously to keep the system usable in dev.
    """

    def __init__(self) -> None:
        self._pool: Any | None = None

    async def _get_pool(self) -> Any:
        if self._pool is None:
            settings = get_settings()
            try:
                self._pool = await create_pool(
                    RedisSettings.from_dsn(settings.redis_url)
                )
            except Exception as exc:
                logger.warning("arq_pool_unavailable", error=str(exc))
                self._pool = None
        return self._pool

    async def enqueue(self, *, entity_type: str, entity_id: UUID) -> None:
        pool = await self._get_pool()
        if pool is None:
            # Sync fallback for tests / when Redis is down
            from src.universe.infrastructure.tasks import refresh_embedding

            await refresh_embedding({}, entity_type=entity_type, entity_id=str(entity_id))
            return
        await pool.enqueue_job(
            "refresh_embedding",
            entity_type=entity_type,
            entity_id=str(entity_id),
        )


# ---------------------------------------------------------------------------
# Debounced full-graph enrichment (R15 slice 2)
# ---------------------------------------------------------------------------
#
# Full-graph relationship enrichment (semantic RELATED_TO + structural edge
# inference over ALL of a user's entities) is expensive and was running inline
# on every chat turn — a chatty conversation paid the graph-wide cost per
# message on the API process. We move it to a coalesced background job.

_enrichment_pool: Any | None = None


async def _get_enrichment_pool() -> Any | None:
    """Cached arq pool for enrichment enqueues, or None if Redis is down.

    Module-level cache so a busy chat doesn't reconnect every turn; the API
    process has a single event loop, so one pool is safe to reuse.
    """
    global _enrichment_pool
    if _enrichment_pool is not None:
        return _enrichment_pool
    try:
        _enrichment_pool = await create_pool(
            RedisSettings.from_dsn(get_settings().redis_url)
        )
    except Exception as exc:
        logger.warning("enrichment_arq_pool_unavailable", error=str(exc))
        _enrichment_pool = None
    return _enrichment_pool


async def enqueue_graph_enrichment(user_id: UUID) -> bool:
    """Enqueue a coalesced full-graph enrichment for *user_id*.

    Debounce: a fixed `_job_id` per user means rapid chat turns collapse into a
    single pending job (arq dedups by job id), and `_defer_by` gives a short
    window for a burst to coalesce before the worker picks it up. arq's kept
    result then rate-limits re-enqueue to roughly once per `keep_result` window
    — full-graph enrichment is idempotent + eventually-consistent, so this is an
    intentional rate-limit, not a loss: the per-turn entity/relation extraction
    still runs inline, so new nodes + their directly-extracted edges appear
    immediately; only INFERRED edges lag by the debounce window.

    Returns True if the job was enqueued OR coalesced into a pending/recent one
    (both mean enrichment IS scheduled — do not run inline). Returns False ONLY
    when the queue is unreachable, so the caller can fall back to running it
    inline. Enrichment therefore NEVER silently stops.
    """
    pool = await _get_enrichment_pool()
    if pool is None:
        return False
    try:
        await pool.enqueue_job(
            "enrich_universe_task",
            user_id=str(user_id),
            _job_id=f"enrich-graph:{user_id}",
            _defer_by=5,
        )
        return True
    except Exception as exc:
        logger.warning("enrich_enqueue_failed", user_id=str(user_id), error=str(exc))
        return False


from typing import Any  # noqa: E402  (used in annotations above)
