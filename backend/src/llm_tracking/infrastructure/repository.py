"""Repository for llm_usage_logs."""
from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import text
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
            cost_eur=log.cost_eur,
            agent=log.agent,
        )
        self._session.add(orm)

    async def get_monthly_summary(
        self, user_id: UUID, year: int, month: int
    ) -> dict[str, Any]:
        """Return aggregated usage for a user in a given month."""
        row = (
            await self._session.execute(
                text(
                    """
                    SELECT
                        COALESCE(SUM(cost_eur), 0) AS total_cost,
                        COALESCE(SUM(total_tokens), 0) AS total_tokens,
                        COALESCE(SUM(input_tokens), 0) AS input_tokens,
                        COALESCE(SUM(output_tokens), 0) AS output_tokens
                    FROM llm_usage_logs
                    WHERE user_id = :uid
                      AND EXTRACT(YEAR FROM created_at) = :year
                      AND EXTRACT(MONTH FROM created_at) = :month
                    """
                ),
                {"uid": str(user_id), "year": year, "month": month},
            )
        ).mappings().one()

        model_rows = (
            await self._session.execute(
                text(
                    """
                    SELECT
                        model,
                        COALESCE(SUM(cost_eur), 0) AS cost,
                        COALESCE(SUM(total_tokens), 0) AS tokens,
                        COUNT(*) AS runs
                    FROM llm_usage_logs
                    WHERE user_id = :uid
                      AND EXTRACT(YEAR FROM created_at) = :year
                      AND EXTRACT(MONTH FROM created_at) = :month
                    GROUP BY model
                    ORDER BY cost DESC
                    """
                ),
                {"uid": str(user_id), "year": year, "month": month},
            )
        ).mappings().all()

        agent_rows = (
            await self._session.execute(
                text(
                    """
                    SELECT
                        COALESCE(agent, 'unknown') AS agent,
                        COALESCE(SUM(cost_eur), 0) AS cost,
                        COALESCE(SUM(total_tokens), 0) AS tokens,
                        COUNT(*) AS runs
                    FROM llm_usage_logs
                    WHERE user_id = :uid
                      AND EXTRACT(YEAR FROM created_at) = :year
                      AND EXTRACT(MONTH FROM created_at) = :month
                    GROUP BY agent
                    ORDER BY runs DESC
                    """
                ),
                {"uid": str(user_id), "year": year, "month": month},
            )
        ).mappings().all()

        return {
            "total_cost_eur": float(row["total_cost"]),
            "total_tokens": int(row["total_tokens"]),
            "input_tokens": int(row["input_tokens"]),
            "output_tokens": int(row["output_tokens"]),
            "by_model": [
                {
                    "model": r["model"],
                    "cost_eur": float(r["cost"]),
                    "tokens": int(r["tokens"]),
                    "runs": int(r["runs"]),
                }
                for r in model_rows
            ],
            "by_agent": [
                {
                    "agent": r["agent"] or "unknown",
                    "cost_eur": float(r["cost"]),
                    "tokens": int(r["tokens"]),
                    "runs": int(r["runs"]),
                }
                for r in agent_rows
            ],
        }

    async def get_daily_breakdown(
        self, user_id: UUID, year: int, month: int
    ) -> list[dict[str, Any]]:
        """Return per-day token usage for a user in a given month."""
        rows = (
            await self._session.execute(
                text(
                    """
                    SELECT
                        DATE(created_at) AS day,
                        COALESCE(SUM(input_tokens), 0) AS input_tokens,
                        COALESCE(SUM(output_tokens), 0) AS output_tokens,
                        COALESCE(SUM(total_tokens), 0) AS total_tokens,
                        COALESCE(SUM(cost_eur), 0) AS cost_eur
                    FROM llm_usage_logs
                    WHERE user_id = :uid
                      AND EXTRACT(YEAR FROM created_at) = :year
                      AND EXTRACT(MONTH FROM created_at) = :month
                    GROUP BY DATE(created_at)
                    ORDER BY day ASC
                    """
                ),
                {"uid": str(user_id), "year": year, "month": month},
            )
        ).mappings().all()
        return [
            {
                "day": str(r["day"]),
                "input_tokens": int(r["input_tokens"]),
                "output_tokens": int(r["output_tokens"]),
                "total_tokens": int(r["total_tokens"]),
                "cost_eur": float(r["cost_eur"]),
            }
            for r in rows
        ]

    async def get_session_breakdown(
        self, user_id: UUID, limit: int = 50
    ) -> list[dict[str, Any]]:
        """Return per-session aggregated usage."""
        rows = (
            await self._session.execute(
                text(
                    """
                    SELECT
                        session_id,
                        COALESCE(SUM(cost_eur), 0) AS cost,
                        COALESCE(SUM(total_tokens), 0) AS tokens,
                        COUNT(*) AS runs,
                        MAX(created_at) AS last_used
                    FROM llm_usage_logs
                    WHERE user_id = :uid
                    GROUP BY session_id
                    ORDER BY last_used DESC
                    LIMIT :limit
                    """
                ),
                {"uid": str(user_id), "limit": limit},
            )
        ).mappings().all()
        return [
            {
                "session_id": r["session_id"] or "unknown",
                "cost_eur": float(r["cost"]),
                "tokens": int(r["tokens"]),
                "runs": int(r["runs"]),
                "last_used": r["last_used"].isoformat() if r["last_used"] else None,
            }
            for r in rows
        ]
