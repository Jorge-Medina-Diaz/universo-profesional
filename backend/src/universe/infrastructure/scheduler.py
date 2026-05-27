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


from typing import Any  # noqa: E402  (used in annotations above)
