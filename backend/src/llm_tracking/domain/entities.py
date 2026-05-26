"""Domain entities for LLM usage tracking."""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Self
from uuid import UUID


@dataclass(frozen=True)
class LlmUsageLog:
    user_id: UUID
    provider: str
    model: str
    input_tokens: int = 0
    output_tokens: int = 0
    cache_read_tokens: int = 0
    cache_write_tokens: int = 0
    total_tokens: int = 0
    duration_ms: int | None = None
    cost_usd: Decimal | None = None
    run_id: str | None = None
    session_id: str | None = None

    @classmethod
    def from_agno_metrics(
        cls,
        *,
        user_id: UUID,
        provider: str,
        model: str,
        metrics: dict[str, object],
        run_id: str | None = None,
        session_id: str | None = None,
    ) -> Self:
        """Build from Agno run metrics dict (ai.agno_sessions.runs->metrics)."""
        return cls(
            user_id=user_id,
            provider=provider,
            model=model,
            input_tokens=_int(metrics.get("input_tokens")),
            output_tokens=_int(metrics.get("output_tokens")),
            cache_read_tokens=_int(metrics.get("cache_read_tokens")),
            cache_write_tokens=_int(metrics.get("cache_write_tokens")),
            total_tokens=_int(metrics.get("total_tokens")),
            duration_ms=_int(metrics.get("duration") * 1000)
            if isinstance(metrics.get("duration"), (int, float))
            else None,
            cost_usd=None,  # computed separately
            run_id=run_id,
            session_id=session_id,
        )


def _int(val: object) -> int:
    try:
        return int(val or 0)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return 0
