"""LLM usage tracking API — user-facing cost and token dashboards."""
from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from fastapi import APIRouter

from src.identity.interfaces.api.deps import CurrentUserId, SessionDep
from src.llm_tracking.infrastructure.repository import SqlalchemyLlmUsageLogRepository

router = APIRouter()


@router.get("/usage")
async def get_usage_summary(
    user_id: CurrentUserId,
    session: SessionDep,
    year: int | None = None,
    month: int | None = None,
) -> dict[str, Any]:
    """Return the user's LLM usage summary for a month.

    Defaults to the current month. Includes total cost, total tokens,
    breakdown by model, and breakdown by agent/specialist.
    """
    now = datetime.utcnow()
    year = year or now.year
    month = month or now.month

    repo = SqlalchemyLlmUsageLogRepository(session)
    summary = await repo.get_monthly_summary(UUID(user_id), year, month)
    daily = await repo.get_daily_breakdown(UUID(user_id), year, month)

    # Free tier monthly token budget for gauge display
    free_tier_tokens = 10_000

    return {
        "period": {"year": year, "month": month},
        "summary": summary,
        "daily": daily,
        "free_tier_tokens": free_tier_tokens,
    }


@router.get("/usage/sessions")
async def get_usage_sessions(
    user_id: CurrentUserId,
    session: SessionDep,
    limit: int = 50,
) -> dict[str, Any]:
    """Return per-session LLM usage breakdown."""
    repo = SqlalchemyLlmUsageLogRepository(session)
    sessions = await repo.get_session_breakdown(UUID(user_id), limit=limit)
    return {"sessions": sessions}
