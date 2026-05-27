"""Base class for Context Providers.

A Context Provider encapsulates:
  1. A knowledge namespace (vector store partition).
  2. A memory scope (semantic + procedural memory filter).
  3. A tool surface (the functions exposed to Agno agents).
  4. A self-learning hook (how feedback is recorded and later recalled).

Providers are stateless; they receive the AsyncSession and user_id on every
call so they can be reused across requests and even processes (horizontal
scaling).
"""
from __future__ import annotations

from collections.abc import Callable
from typing import Any
from uuid import UUID

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

logger = structlog.get_logger(__name__)


class BaseContextProvider:
    """Abstract context provider.  Concrete providers override:
      • name / knowledge_namespace / memory_scope
      • get_tools() → list of Agno-compatible callables
      • get_memory_context() → str injected into agent instructions
    """

    name: str = "base"
    knowledge_namespace: str = "default"
    memory_scope: str = "global"

    def __init__(self, session: AsyncSession, user_id: UUID) -> None:
        self._session = session
        self._user_id = user_id

    # ------------------------------------------------------------------
    # Tool surface — overridden by each provider
    # ------------------------------------------------------------------

    def get_tools(self) -> list[Callable[..., Any]]:
        """Return the list of Agno tools this provider exposes.

        The Intent Router uses this to decide which provider can handle a
        user intent.  Each tool is a callable decorated with @tool or a
        plain async function that Agno will wrap.
        """
        return []

    # ------------------------------------------------------------------
    # Memory context — injected into the agent system prompt
    # ------------------------------------------------------------------

    async def get_memory_context(self) -> str:
        """Build a concise context string from semantic + procedural memory.

        This is prepended to the agent's instructions so the agent knows
        the user's preferences and learned rules for this scope.
        """
        facts = await self._load_semantic_facts()
        rules = await self._load_procedural_rules()
        parts: list[str] = []
        if facts:
            parts.append("## Hechos conocidos del usuario")
            for f in facts:
                parts.append(f"- {f['category']}/{f['key']}: {f['value']} (confianza {f['confidence']})")
        if rules:
            parts.append("## Reglas aprendidas para este ámbito")
            for r in rules:
                parts.append(f"- Si '{r['trigger_pattern']}' → {r['action_rule']} (éxito {r['success_rate']:.0%})")
        return "\n".join(parts) if parts else ""

    # ------------------------------------------------------------------
    # Self-learning hooks
    # ------------------------------------------------------------------

    async def record_feedback(
        self,
        *,
        trigger: str,
        expected_action: str,
        actual_action: str,
        was_correct: bool,
    ) -> None:
        """Store a correction so the agent improves next time.

        Called by the HITL layer or by explicit user feedback (thumbs up/down).
        """
        from datetime import UTC, datetime

        from src.agents.memory.structured_memory import UserProceduralMemoryOrm

        if was_correct:
            # Reinforce existing rule or create a positive one
            rule = UserProceduralMemoryOrm(
                user_id=self._user_id,
                scope=self.memory_scope,
                trigger_pattern=trigger,
                action_rule=expected_action,
                hit_count=1,
                success_rate=1.0,
                active=True,
                created_at=datetime.now(UTC),
                updated_at=datetime.now(UTC),
            )
            self._session.add(rule)
            await self._session.flush()
            logger.info(
                "procedural_memory_recorded",
                user_id=str(self._user_id),
                scope=self.memory_scope,
                trigger=trigger,
            )
        else:
            # Negative example: either create a "do NOT" rule or deactivate
            # a conflicting positive rule.
            rule = UserProceduralMemoryOrm(
                user_id=self._user_id,
                scope=self.memory_scope,
                trigger_pattern=trigger,
                action_rule=f"NO HACER: {actual_action}. En su lugar: {expected_action}",
                hit_count=1,
                success_rate=0.0,
                active=True,
                created_at=datetime.now(UTC),
                updated_at=datetime.now(UTC),
            )
            self._session.add(rule)
            await self._session.flush()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _load_semantic_facts(self, limit: int = 20) -> list[dict[str, Any]]:
        from sqlalchemy import text

        rows = (
            await self._session.execute(
                text(
                    """
                    SELECT category, key, value, confidence
                    FROM user_semantic_memory
                    WHERE user_id = :uid AND category = ANY(:cats)
                    ORDER BY confidence DESC, updated_at DESC
                    LIMIT :lim
                    """
                ),
                {
                    "uid": str(self._user_id),
                    "cats": [self.memory_scope, "global"],
                    "lim": limit,
                },
            )
        ).mappings().all()
        return [dict(r) for r in rows]

    async def _load_procedural_rules(self, limit: int = 10) -> list[dict[str, Any]]:
        from sqlalchemy import text

        rows = (
            await self._session.execute(
                text(
                    """
                    SELECT trigger_pattern, action_rule, success_rate
                    FROM user_procedural_memory
                    WHERE user_id = :uid AND scope = :scope AND active = true
                    ORDER BY success_rate DESC, hit_count DESC
                    LIMIT :lim
                    """
                ),
                {
                    "uid": str(self._user_id),
                    "scope": self.memory_scope,
                    "lim": limit,
                },
            )
        ).mappings().all()
        return [dict(r) for r in rows]
