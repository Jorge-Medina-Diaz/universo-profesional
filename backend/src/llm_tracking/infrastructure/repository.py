"""Repository for llm_usage_logs."""
from __future__ import annotations

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.llm_tracking.domain.entities import LlmUsageLog
from src.llm_tracking.infrastructure.orm import LlmUsageLogORM


class SqlalchemyLlmUsageLogRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, log: LlmUsageLog) -> None:
        orm = LlmUsageLogORM(
            user_id=log.user_id,
            run_id=log.run_id,
            session_id=log.session_id,
            provider=log.provider,
            model=log.model,
            input_tokens=log.input_tokens,
            output_tokens=log.output_tokens,
            cache_read_tokens=log.cache_read_tokens,
            cache_write_tokens=log.cache_write_tokens,
            total_tokens=log.total_tokens,
            duration_ms=log.duration_ms,
            cost_usd=log.cost_usd,
        )
        self._session.add(orm)
