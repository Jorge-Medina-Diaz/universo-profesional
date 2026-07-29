"""Arq-backed scheduler that enqueues embedding-refresh jobs."""
from __future__ import annotations

from typing import Any
from uuid import UUID

import structlog

from src.universe.application.ports import EmbeddingRefreshScheduler

logger = structlog.get_logger(__name__)


class ArqEmbeddingScheduler(EmbeddingRefreshScheduler):
    """Enqueue an embedding-refresh job on Redis.

    When the queue is unreachable we SKIP and let the transactional outbox
    backfill. There used to be an in-process fallback here that ran
    `refresh_embedding` synchronously, and it deadlocked:

      * `enqueue()` is called from the CRUD use case *inside* the caller's
        still-open transaction, which holds a row lock on the entity;
      * `refresh_embedding` opens its OWN session and issues
        `UPDATE <table> SET embedding = …` against that same row;
      * so it blocked on a lock the caller could only release by committing —
        which it could not do, because it was awaiting this call.

    Every entity write hung for as long as Redis was down. Skipping is both
    safe and already the documented design: embeddings are written at request
    time as at-most-once fire-and-forget, and
    `universe.infrastructure.projections.project_embeddings_task` is the
    reliability net that repairs anything lost, within a tick.
    """

    async def _get_pool(self) -> Any:
        from src.shared.arq_pool import get_arq_pool

        return await get_arq_pool()

    async def enqueue(self, *, entity_type: str, entity_id: UUID) -> None:
        pool = await self._get_pool()
        if pool is None:
            logger.warning(
                "embedding_enqueue_skipped_no_queue",
                entity_type=entity_type,
                entity_id=str(entity_id),
                detail="queue unreachable; the outbox projection will backfill",
            )
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



async def _get_enrichment_pool() -> Any | None:
    """Cached arq pool for enrichment enqueues, or None if Redis is down.

    One pool PER PROCESS, created LAZILY on first use. Lazy-after-fork is what
    keeps this safe under a multi-worker (Gunicorn) deploy — each worker builds
    its own pool bound to its own event loop. Do NOT eagerly initialise this at
    app startup: a pool created before the fork would share sockets across
    workers and corrupt. Same pattern as integrations/infrastructure/queue.py.
    """
    from src.shared.arq_pool import get_arq_pool

    return await get_arq_pool()


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
