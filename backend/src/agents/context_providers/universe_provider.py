"""UniverseContextProvider — Everything related to the professional profile.

Knowledge namespace: "universe"
Memory scope: "universe_updates"
Tools: retrieval, graph exploration, CRUD proposals, enrichment.
"""
from __future__ import annotations

from collections.abc import Callable
from typing import Any

from src.agents.context_providers.base import BaseContextProvider
from src.agents.tools.discovery_tools import (
    get_profile_completeness,
    suggest_discovery_questions,
)
from src.agents.tools.graph_query_tools import explain_graph_query, query_graph
from src.agents.tools.learning_tools import record_agent_feedback
from src.agents.tools.retrieval_tools import (
    enrich_universe,
    explain_path,
    get_career_pillars,
    get_graph_neighbors,
    universe_retrieve,
)
from src.agents.tools.ui_widgets import (
    propose_achievement,
    propose_certification,
    propose_course,
    propose_education,
    propose_experience,
    propose_language,
    propose_project,
    propose_skill,
)


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

    def get_tools(self) -> list[Callable[..., Any]]:
        return [
            # Retrieval
            universe_retrieve,
            get_graph_neighbors,
            explain_path,
            get_career_pillars,
            enrich_universe,
            # Discovery (conversational profile building)
            get_profile_completeness,
            suggest_discovery_questions,
            # Self-learning feedback
            record_agent_feedback,
            # Graph reasoning (Text2Cypher)
            query_graph,
            explain_graph_query,
            # HITL proposals (one per entity kind)
            propose_experience,
            propose_education,
            propose_project,
            propose_skill,
            propose_certification,
            propose_course,
            propose_language,
            propose_achievement,
        ]
