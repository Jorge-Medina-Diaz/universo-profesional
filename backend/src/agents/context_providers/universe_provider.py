"""UniverseContextProvider — Everything related to the professional profile.

Knowledge namespace: "universe"
Memory scope: "universe_updates"
Tools: retrieval, graph exploration, CRUD proposals, enrichment.
"""
from __future__ import annotations

from src.agents.context_providers.base import BaseContextProvider


class UniverseContextProvider(BaseContextProvider):
    name = "universe_curator"
    knowledge_namespace = "universe"
    memory_scope = "universe_updates"

    async def get_memory_context(self) -> str:
        """Inject profile counts + base semantic/procedural memory."""
        base = await super().get_memory_context()
        # Counts come from the igraph snapshot. Raw `SELECT FROM
        # universe_personal.<Label>` is the documented landmine: label tables
        # don't exist until the first vertex (fresh users 500'd) and a plain
        # SELECT through the cypher wrapper is a syntax error — this silently
        # degraded the intent provider context on every new-user turn.
        from collections import Counter

        from src.graph.application.retrieval import _load_snapshot
        from src.graph.domain import schema as graph_schema

        snapshot = await _load_snapshot(self._session, self._user_id)
        kind_counter = Counter(
            meta[1] for meta in snapshot.idx_to_meta.values() if meta[1]
        )
        counts = [
            f"  {kind}: {kind_counter.get(kind, 0)}"
            for kind in graph_schema.KIND_TO_LABEL
        ]

        profile_block = "## Perfil actual del usuario\n" + "\n".join(counts)
        parts = [profile_block]
        if base:
            parts.append(base)
        return "\n\n".join(parts)
