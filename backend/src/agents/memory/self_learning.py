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
from typing import Any
from uuid import UUID

import structlog
from sqlalchemy import text
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

    async def consolidate(self, user_id: UUID, min_examples: int = 3) -> int:
        """Aggregate similar feedback rows into refined rules.

        Returns the number of consolidated rules created.
        """
        # Fetch recent feedback rows for this user
        rows = (
            await self._session.execute(
                text(
                    """
                    SELECT scope, trigger_pattern, action_rule, success_rate
                    FROM user_procedural_memory
                    WHERE user_id = :uid
                      AND hit_count = 1
                      AND created_at > now() - interval '7 days'
                    ORDER BY scope, trigger_pattern
                    """
                ),
                {"uid": str(user_id)},
            )
        ).mappings().all()

        if len(rows) < min_examples:
            return 0

        # Simple consolidation: group by exact scope + trigger_pattern
        # and average success_rate.  In Sprint S we can upgrade this to
        # semantic clustering over trigger_pattern embeddings.
        groups: dict[tuple[str, str], list[dict[str, Any]]] = {}
        for r in rows:
            key = (r["scope"], r["trigger_pattern"])
            groups.setdefault(key, []).append(dict(r))

        consolidated = 0
        for (scope, trigger), examples in groups.items():
            if len(examples) < min_examples:
                continue
            avg_success = sum(e["success_rate"] for e in examples) / len(examples)
            best_action = max(examples, key=lambda e: e["success_rate"])["action_rule"]

            # Deactivate the raw examples
            await self._session.execute(
                text(
                    """
                    UPDATE user_procedural_memory
                    SET active = false
                    WHERE user_id = :uid
                      AND scope = :scope
                      AND trigger_pattern = :trigger
                      AND hit_count = 1
                    """
                ),
                {"uid": str(user_id), "scope": scope, "trigger": trigger},
            )

            # Insert the consolidated rule
            from src.agents.memory.structured_memory import UserProceduralMemoryOrm

            rule = UserProceduralMemoryOrm(
                user_id=user_id,
                scope=scope,
                trigger_pattern=trigger,
                action_rule=best_action,
                hit_count=len(examples),
                success_rate=round(avg_success, 2),
                active=True,
                created_at=datetime.now(UTC),
                updated_at=datetime.now(UTC),
            )
            self._session.add(rule)
            consolidated += 1

        await self._session.flush()
        logger.info("memory_consolidated", user_id=str(user_id), rules_created=consolidated)
        return consolidated

    async def get_active_rules(self, user_id: UUID, scope: str, limit: int = 10) -> list[dict[str, Any]]:
        """Return the best rules for a given scope."""
        rows = (
            await self._session.execute(
                text(
                    """
                    SELECT trigger_pattern, action_rule, success_rate, hit_count
                    FROM user_procedural_memory
                    WHERE user_id = :uid AND scope = :scope AND active = true
                    ORDER BY success_rate DESC, hit_count DESC
                    LIMIT :lim
                    """
                ),
                {"uid": str(user_id), "scope": scope, "lim": limit},
            )
        ).mappings().all()
        return [dict(r) for r in rows]
