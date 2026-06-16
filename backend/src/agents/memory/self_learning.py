"""Self-Learning Loop — turn user feedback into procedural memory.

When the user corrects an agent action (e.g. edits a proposed skill,
rejects a CV template, or gives thumbs down), the system records:
  • What triggered the action (context / user message)
  • What the agent did
  • What the user expected instead
  • Whether it was a positive or negative example

Over time these examples are consolidated into active procedural rules
that the Context Providers inject into agent instructions.

The loop is designed to be cheap (no GPU, no fine-tuning) — it is purely
context engineering: better prompts through accumulated experience.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

logger = structlog.get_logger(__name__)


# ---------------------------------------------------------------------------
# Feedback types
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class UserFeedback:
    user_id: UUID
    session_id: str
    scope: str  # e.g. "universe_updates", "document_generation"
    trigger_message: str
    agent_action: str
    user_expectation: str
    sentiment: str  # "positive" | "negative" | "neutral"
    correction_detail: str | None = None


# ---------------------------------------------------------------------------
# Learning engine
# ---------------------------------------------------------------------------


class SelfLearningEngine:
    """Record feedback and periodically consolidate into rules."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def record(self, feedback: UserFeedback) -> None:
        """Store a single feedback event."""
        from src.agents.memory.structured_memory import UserProceduralMemoryOrm

        # Compute initial success rate from sentiment
        success_rate = {"positive": 1.0, "negative": 0.0, "neutral": 0.5}.get(
            feedback.sentiment, 0.5
        )

        rule = UserProceduralMemoryOrm(
            user_id=feedback.user_id,
            scope=feedback.scope,
            trigger_pattern=feedback.trigger_message[:500],
            action_rule=feedback.user_expectation[:2000],
            hit_count=1,
            success_rate=success_rate,
            active=True,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        self._session.add(rule)
        await self._session.flush()

        logger.info(
            "feedback_recorded",
            user_id=str(feedback.user_id),
            scope=feedback.scope,
            sentiment=feedback.sentiment,
        )
