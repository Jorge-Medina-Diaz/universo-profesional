"""UniverseContextProvider — Everything related to the professional profile.

Knowledge namespace: "universe"
Memory scope: "universe_updates"
Tools: retrieval, graph exploration, CRUD proposals, enrichment.
"""
from __future__ import annotations

from typing import Any, Callable

from agno.tools import tool

from src.agents.context_providers.base import BaseContextProvider
from src.agents.tools.graph_query_tools import explain_graph_query, query_graph
from src.agents.tools.discovery_tools import (
    get_profile_completeness,
    suggest_discovery_questions,
)
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
        from uuid import UUID
        from src.graph.application.universe_graph import universe_graph_service
        from src.graph.domain import schema as graph_schema

        counts: list[str] = []
        for kind, label in graph_schema.KIND_TO_LABEL.items():
            result = await universe_graph_service._execute_cypher(
                self._session,
                f"""
                SELECT count(*)::int AS n
                FROM {graph_schema.GRAPH_PERSONAL}.{label}
                WHERE v.user_id = $uid
                """,
                {"uid": str(self._user_id)},
            )
            n = result[0]["n"] if result else 0
            counts.append(f"  {kind}: {n}")

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
