"""AGE-backed implementation of the :class:`~src.graph.application.ports.GraphRepository` port.

This is a thin adapter around the low-level ``age_client`` so the
application layer never imports infrastructure directly.
"""
from __future__ import annotations

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from src.graph.infrastructure.age_client import cypher, ensure_age_loaded, parse_agtype


class AgeGraphRepository:
    """Concrete adapter for Apache AGE."""

    async def execute(
        self,
        session: AsyncSession,
        graph: str,
        query: str,
        *,
        params: dict[str, Any] | None = None,
        column_defs: str = "result agtype",
    ) -> list[dict[str, Any]]:
        return await cypher(session, graph, query, params=params, column_defs=column_defs)

    def parse_result(self, value: Any) -> Any:
        return parse_agtype(value)

    async def ensure_loaded(self, session: AsyncSession) -> None:
        await ensure_age_loaded(session)


# Module-level singleton — cheap to share because it is stateless.
age_graph_repository = AgeGraphRepository()
