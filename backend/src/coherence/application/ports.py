"""Ports — interfaces the coherence engine depends on.

Keeps the use case layer free of SQLAlchemy / pgvector references; concrete
implementations live in `coherence/infrastructure/`.
"""
from __future__ import annotations

from typing import Any, Protocol
from uuid import UUID


class ChangeLogRepository(Protocol):
    async def record(
        self,
        *,
        user_id: UUID,
        entity_type: str,
        entity_id: UUID,
        change_type: str,
        field: str | None,
        old_value: Any,
        new_value: Any,
        reason: str | None,
        source: str,
        agent_run_id: str | None = None,
    ) -> None: ...

    async def list_for_user(
        self,
        *,
        user_id: UUID,
        limit: int = 50,
        since: Any | None = None,
        cursor: str | None = None,
    ) -> dict[str, Any]:
        """Keyset-paginated change feed: {"items": [...], "next_cursor": str|None}."""
        ...

    async def list_for_entity(
        self,
        *,
        user_id: UUID,
        entity_type: str,
        entity_id: UUID,
        limit: int = 20,
    ) -> list[dict[str, Any]]: ...


class SemanticMatcher(Protocol):
    async def find_most_similar(
        self,
        *,
        user_id: UUID,
        entity_type: str,
        text: str,
        threshold: float = 0.85,
        top_k: int = 3,
    ) -> list[dict[str, Any]]:
        """Return list of {'entity_id': UUID, 'score': float} above threshold."""
        ...
