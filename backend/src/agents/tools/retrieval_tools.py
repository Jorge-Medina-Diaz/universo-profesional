"""Retrieval tools — server-side, used by every specialist.

Three Agno tools that expose the Sprint O hybrid retriever to the chat
coordinator + specialists:

  • `universe_retrieve(query, kinds?, top_k=12)` — ranked entities from
    the user's graph using BM25 + dense + PPR + RRF.
  • `get_graph_neighbors(entity_id, depth=1, edge_kinds?)` — explore the
    vicinity of a focus node, returning typed-edge context.
  • `explain_path(from_id, to_id, max_len=4)` — shortest path between
    two entities, useful for "how is X related to Y" questions.

These replace the Sprint G `search_universe`, `find_existing` (for
read-only contexts), and most of `search_rubrics` calls — Sprint Q will
update each specialist's prompt to prefer them.
"""
from __future__ import annotations

from typing import Any
from uuid import UUID

import structlog
from agno.run.base import RunContext
from agno.tools import tool

from src.graph.application.retrieval import hybrid_retrieve
from src.graph.application.universe_graph import universe_graph_service
from src.graph.domain import schema as graph_schema
from src.graph.infrastructure.age_client import cypher, parse_agtype
from src.shared.db import get_session_factory, set_rls_user

logger = structlog.get_logger(__name__)


@tool(
    name="universe_retrieve",
    description=(
        "Search the user's professional graph universe. Fuses three "
        "retrieval signals (keyword BM25, semantic similarity, "
        "structural PPR over the graph) with reciprocal-rank-fusion. "
        "Returns ranked entities — skills, projects, experiences, "
        "artifacts, decisions, etc. Pass `kinds` (comma-separated) to "
        "scope to specific entity kinds (e.g. 'skill,project'). "
        "Top-K defaults to 12. The result `contributions` field shows "
        "which lanes ranked each item — useful for explaining matches "
        "or detecting domain drift."
    ),
)
async def universe_retrieve(
    run_context: RunContext,
    query: str,
    kinds: str | None = None,
    top_k: int = 12,
) -> dict[str, Any]:
    user_id_raw = run_context.user_id
    if not user_id_raw:
        return {"ok": False, "error": "missing user_id", "items": []}
    user_id = UUID(str(user_id_raw))
    factory = get_session_factory()
    kinds_list = (
        [k.strip() for k in kinds.split(",") if k.strip()] if kinds else None
    )
    async with factory() as session:
        await set_rls_user(session, user_id)
        items = await hybrid_retrieve(
            session, user_id, query, top_k=top_k, kinds=kinds_list
        )
    return {
        "ok": True,
        "items": [
            {
                "entity_id": str(item.entity_id),
                "kind": item.kind,
                "name": item.name,
                "fused_score": round(item.fused_score, 6),
                "contributions": item.contributions,
            }
            for item in items
        ],
    }


@tool(
    name="get_graph_neighbors",
    description=(
        "Return the typed neighbourhood of an entity up to `depth` hops "
        "(1-4). Filter by edge type via `edge_kinds` (comma-separated, "
        "uppercase). Use this to ground a follow-up question: e.g., "
        "after the user asks 'what evidences my Python skill?' the "
        "specialist calls get_graph_neighbors with the skill id and "
        "depth=1 to surface the DEMONSTRATES edges."
    ),
)
async def get_graph_neighbors(
    run_context: RunContext,
    entity_id: str,
    depth: int = 1,
    edge_kinds: str | None = None,
    include_expired: bool = False,
) -> dict[str, Any]:
    user_id_raw = run_context.user_id
    if not user_id_raw:
        return {"ok": False, "error": "missing user_id", "items": []}
    user_id = UUID(str(user_id_raw))
    factory = get_session_factory()
    edge_kinds_list: list[str] | None = None
    if edge_kinds:
        edge_kinds_list = [k.strip() for k in edge_kinds.split(",") if k.strip()]
    async with factory() as session:
        await set_rls_user(session, user_id)
        items = await universe_graph_service.neighbors(
            session,
            entity_id=UUID(entity_id),
            user_id=user_id,
            depth=depth,
            edge_kinds=edge_kinds_list,
            include_expired=include_expired,
        )
    return {"ok": True, "items": items}


@tool(
    name="explain_path",
    description=(
        "Return the shortest typed path between two entities — useful "
        "for 'how is X related to Y' questions, or for surfacing the "
        "evidence chain behind a claim. `max_len` caps the search depth "
        "(default 4)."
    ),
)
async def explain_path(
    run_context: RunContext,
    from_entity_id: str,
    to_entity_id: str,
    max_len: int = 4,
) -> dict[str, Any]:
    user_id_raw = run_context.user_id
    if not user_id_raw:
        return {"ok": False, "error": "missing user_id", "paths": []}
    user_id = UUID(str(user_id_raw))
    if max_len < 1 or max_len > 6:
        return {"ok": False, "error": "max_len must be 1..6", "paths": []}
    factory = get_session_factory()
    async with factory() as session:
        await set_rls_user(session, user_id)
        rows = await cypher(
            session,
            graph_schema.GRAPH_PERSONAL,
            (
                f"MATCH p = shortestPath("
                f"  (a:Entity {{id: $from_id, user_id: $uid}})-[*..{max_len}]-"
                f"  (b:Entity {{id: $to_id, user_id: $uid}})) "
                f"RETURN nodes(p), relationships(p)"
            ),
            params={
                "from_id": from_entity_id,
                "to_id": to_entity_id,
                "uid": str(user_id),
            },
            column_defs="nodes agtype, rels agtype",
        )
    paths: list[dict[str, Any]] = []
    for row in rows:
        nodes = parse_agtype(row.get("nodes"))
        rels = parse_agtype(row.get("rels"))
        paths.append({"nodes": nodes, "edges": rels})
    return {"ok": True, "paths": paths}


ALL_RETRIEVAL_TOOLS = [universe_retrieve, get_graph_neighbors, explain_path]
