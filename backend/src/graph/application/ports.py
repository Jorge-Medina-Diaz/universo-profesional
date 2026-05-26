"""Abstract ports for graph storage adapters.

The application layer depends on these protocols, never on concrete
infrastructure (AGE, Neo4j, etc.). Implementations live in
``graph/infrastructure/``.
"""
from __future__ import annotations

from typing import Any, Protocol
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession


class GraphRepository(Protocol):
    """Port for executing Cypher-like queries against a property-graph backend."""

    async def execute(
        self,
        session: AsyncSession,
        graph: str,
        query: str,
        *,
        params: dict[str, Any] | None = None,
        column_defs: str = "result agtype",
    ) -> list[dict[str, Any]]:
        """Run a query and return a list of row dicts.

        Each value is the raw serialised form — call :meth:`parse_result`
        to turn it into a Python object.
        """
        ...

    def parse_result(self, value: Any) -> Any:
        """Parse a raw query value (e.g. agtype string) into a Python object."""
        ...

    async def ensure_loaded(self, session: AsyncSession) -> None:
        """Idempotent per-session setup (search_path, extension load, …)."""
        ...
