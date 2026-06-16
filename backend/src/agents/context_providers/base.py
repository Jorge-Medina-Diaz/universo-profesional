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
