"""Learning tools — let agents record feedback for the self-learning loop.

These tools wire the HITL rejection/editing flow into the SelfLearningEngine
so the agent improves over time without fine-tuning.
"""
from __future__ import annotations

from typing import Any

import structlog
from agno.tools import tool

from src.agents.memory.self_learning import SelfLearningEngine, UserFeedback

logger = structlog.get_logger(__name__)


@tool(description="Record user feedback after a proposal or action.")
async def record_agent_feedback(
    run_context: Any,
    trigger_message: str,
    agent_action: str,
    user_expectation: str,
    sentiment: str = "negative",
    correction_detail: str | None = None,
) -> dict[str, str]:
    """Store feedback so the system learns from mistakes and successes.

    Call this when:
      • A user rejects a propose_* card (sentiment="negative").
      • A user edits a proposed entity heavily (sentiment="neutral").
      • A user confirms with enthusiasm (sentiment="positive").

    Parameters
    ----------
    trigger_message: the user message that led to the agent action.
    agent_action: what the agent did (e.g. "proposed_skill: Docker").
    user_expectation: what the user wanted instead (e.g. "not a skill" or
                      "should have proposed Kubernetes").
    sentiment: "positive" | "negative" | "neutral".
    correction_detail: optional extra context.
    """
    from uuid import UUID

    user_id = UUID(str(run_context.user_id))
    session = run_context.session
    scope = getattr(run_context, "memory_scope", "universe_updates")

    engine = SelfLearningEngine(session)
    feedback = UserFeedback(
        user_id=user_id,
        session_id=getattr(run_context, "session_id", ""),
        scope=scope,
        trigger_message=trigger_message,
        agent_action=agent_action,
        user_expectation=user_expectation,
        sentiment=sentiment,
        correction_detail=correction_detail,
    )
    await engine.record(feedback)
    await session.commit()

    logger.info(
        "agent_feedback_recorded",
        user_id=str(user_id),
        sentiment=sentiment,
        action=agent_action,
    )
    return {"status": "recorded"}
