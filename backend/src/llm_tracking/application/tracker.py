"""Cost calculator + usage logger for LLM calls.

Pricing is hard-coded per model slug. When Anthropic/OpenAI change prices
we update the dict here and redeploy — no DB migration needed.
"""
from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.llm_tracking.domain.entities import LlmUsageLog
from src.llm_tracking.infrastructure.repository import SqlalchemyLlmUsageLogRepository

# USD per 1M tokens
_PRICES: dict[str, dict[str, Decimal]] = {
    "claude-sonnet-4-6": {
        "input": Decimal("3.00"),
        "output": Decimal("15.00"),
        "cache_read": Decimal("0.30"),
        "cache_write": Decimal("3.75"),
    },
    "claude-haiku-4-5-20251001": {
        "input": Decimal("0.80"),
        "output": Decimal("4.00"),
        "cache_read": Decimal("0.08"),
        "cache_write": Decimal("1.00"),
    },
    "gpt-4o": {
        "input": Decimal("2.50"),
        "output": Decimal("10.00"),
        "cache_read": Decimal("1.25"),
        "cache_write": Decimal("0.00"),
    },
    "gpt-4o-mini": {
        "input": Decimal("0.15"),
        "output": Decimal("0.60"),
        "cache_read": Decimal("0.075"),
        "cache_write": Decimal("0.00"),
    },
}


def compute_cost_usd(*, model: str, input_tokens: int, output_tokens: int, cache_read_tokens: int = 0, cache_write_tokens: int = 0) -> Decimal | None:
    """Return estimated cost in USD, or None if model pricing unknown."""
    prices = _PRICES.get(model)
    if not prices:
        return None
    cost = (
        Decimal(input_tokens) * prices["input"]
        + Decimal(output_tokens) * prices["output"]
        + Decimal(cache_read_tokens) * prices["cache_read"]
        + Decimal(cache_write_tokens) * prices["cache_write"]
    ) / Decimal("1_000_000")
    return cost.quantize(Decimal("0.00000001"), rounding=ROUND_HALF_UP)


async def log_agno_run(
    session: AsyncSession,
    *,
    user_id: UUID,
    run_id: str,
    session_id: str,
    metrics: dict[str, Any],
) -> LlmUsageLog | None:
    """Extract metrics from an Agno run and persist a usage log row.

    Returns the created log (with cost computed) or None if metrics are empty.
    """
    # Agno stores model details inside metrics.details.model[0]
    details = metrics.get("details") or {}
    model_info = details.get("model") or [{}]
    first_model = model_info[0] if isinstance(model_info, list) else {}
    provider = first_model.get("provider", "unknown")
    model = first_model.get("id", "unknown")

    if not metrics.get("total_tokens") and not metrics.get("input_tokens"):
        # Mock run or empty metrics — skip cost tracking
        return None

    log = LlmUsageLog.from_agno_metrics(
        user_id=user_id,
        provider=provider,
        model=model,
        metrics=metrics,
        run_id=run_id,
        session_id=session_id,
    )
    cost = compute_cost_usd(
        model=model,
        input_tokens=log.input_tokens,
        output_tokens=log.output_tokens,
        cache_read_tokens=log.cache_read_tokens,
        cache_write_tokens=log.cache_write_tokens,
    )
    # Rebuild with cost (dataclass is frozen, so create new instance)
    log = LlmUsageLog(
        user_id=log.user_id,
        provider=log.provider,
        model=log.model,
        input_tokens=log.input_tokens,
        output_tokens=log.output_tokens,
        cache_read_tokens=log.cache_read_tokens,
        cache_write_tokens=log.cache_write_tokens,
        total_tokens=log.total_tokens,
        duration_ms=log.duration_ms,
        cost_usd=cost,
        run_id=log.run_id,
        session_id=log.session_id,
    )
    repo = SqlalchemyLlmUsageLogRepository(session)
    await repo.create(log)
    return log


async def log_document_llm_call(
    session: AsyncSession,
    *,
    user_id: UUID,
    provider: str,
    model: str,
    input_tokens: int,
    output_tokens: int,
    cache_read_tokens: int = 0,
    cache_write_tokens: int = 0,
    duration_ms: int | None = None,
) -> LlmUsageLog:
    """Persist usage from a direct LLM call (document generation, extraction)."""
    cost = compute_cost_usd(
        model=model,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        cache_read_tokens=cache_read_tokens,
        cache_write_tokens=cache_write_tokens,
    )
    log = LlmUsageLog(
        user_id=user_id,
        provider=provider,
        model=model,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        cache_read_tokens=cache_read_tokens,
        cache_write_tokens=cache_write_tokens,
        total_tokens=input_tokens + output_tokens,
        duration_ms=duration_ms,
        cost_usd=cost,
    )
    repo = SqlalchemyLlmUsageLogRepository(session)
    await repo.create(log)
    return log
