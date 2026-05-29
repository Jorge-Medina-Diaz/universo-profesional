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

from src.agents.tools._deps import require_user_id
from src.graph.application.retrieval import _load_snapshot, hybrid_retrieve
from src.graph.application.universe_graph import universe_graph_service
from src.shared.db import with_user_session

logger = structlog.get_logger(__name__)


@require_user_id
@tool(
    name="enrich_universe",
    description=(
        "Enriquece el universo del usuario infiriendo relaciones entre sus "
        "entidades y conectándolo como un grafo coherente: similitud semántica "
        "→ RELATED_TO, stack de proyectos/experiencias → USES_TECH a skills, y "
        "proyectos solapados con experiencias → PART_OF. Calcula embeddings que "
        "falten. Las aristas se escriben con source='inferred' + confianza y son "
        "refinables. Úsalo cuando el usuario pida 'conecta/enriquece mi universo' "
        "o cuando veas el grafo disperso/pobre. Devuelve el conteo por tipo."
    ),
)
async def enrich_universe(run_context: RunContext) -> dict[str, Any]:
    user_id_raw = run_context.user_id
    user_id = UUID(str(user_id_raw))
    from src.universe.application.enrichment import enrich_user_graph

    async with with_user_session(user_id) as session:
        stats = await enrich_user_graph(session, user_id)
    return {"ok": True, "stats": stats.as_dict()}


@require_user_id
@tool(
    name="get_career_pillars",
    description=(
        "Devuelve los 'pilares de carrera' del usuario: las comunidades "
        "(clusters Leiden) detectadas sobre su grafo, cada una con una etiqueta "
        "y un resumen generado. Úsalo para preguntas globales/temáticas ('¿cuál "
        "es mi narrativa profesional?', '¿cuáles son mis fortalezas?', 'resume mi "
        "perfil') en vez de retrieval entidad a entidad. Si está vacío, sugiere "
        "ejecutar enrich_universe primero."
    ),
)
async def get_career_pillars(run_context: RunContext) -> dict[str, Any]:
    user_id_raw = run_context.user_id
    user_id = UUID(str(user_id_raw))
    from src.graph.application.communities import get_communities

    async with with_user_session(user_id) as session:
        items = await get_communities(session, user_id)
    return {"ok": True, "pillars": items, "count": len(items)}


@require_user_id
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
    user_id = UUID(str(user_id_raw))
    async with with_user_session(user_id) as session:
        kinds_list = [k.strip() for k in kinds.split(",") if k.strip()] if kinds else None
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


@require_user_id
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
    user_id = UUID(str(user_id_raw))
    edge_kinds_list = (
        [e.strip().upper() for e in edge_kinds.split(",") if e.strip()] if edge_kinds else None
    )
    async with with_user_session(user_id) as session:
        items = await universe_graph_service.neighbors(
            session,
            entity_id=UUID(entity_id),
            user_id=user_id,
            depth=depth,
            edge_kinds=edge_kinds_list,
            include_expired=include_expired,
        )
        # AGE vertices don't store the human name — hydrate it from the
        # snapshot so the agent gets useful labels, and slim the payload.
        snap = await _load_snapshot(session, user_id)
        name_by_id = {str(eid): name for eid, _kind, name in snap.idx_to_meta.values()}
    slim = [
        {
            "id": str(it.get("id")),
            "kind": it.get("kind"),
            "name": name_by_id.get(str(it.get("id")), ""),
        }
        for it in items
        if it.get("id")
    ]
    return {"ok": True, "items": slim}


@require_user_id
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
    user_id = UUID(str(user_id_raw))
    if max_len < 1 or max_len > 6:
        return {"ok": False, "error": "max_len must be 1..6", "paths": []}
    # AGE 1.5 lacks shortestPath()/relationships()/nodes(); compute over the
    # in-memory igraph snapshot instead (per-user graphs are tiny, and the
    # snapshot already carries names for a readable path).
    async with with_user_session(user_id) as session:
        snap = await _load_snapshot(session, user_id)
    try:
        src = snap.id_to_idx.get(UUID(from_entity_id))
        dst = snap.id_to_idx.get(UUID(to_entity_id))
    except (ValueError, TypeError):
        return {"ok": False, "error": "invalid entity id", "paths": []}
    if src is None or dst is None:
        return {"ok": True, "paths": []}
    try:
        idx_paths = snap.graph.get_shortest_paths(src, to=dst, mode="all")
    except Exception as exc:
        logger.warning("explain_path_failed", error=str(exc))
        return {"ok": True, "paths": []}
    paths: list[dict[str, Any]] = []
    for p in idx_paths:
        if not p or (len(p) - 1) > max_len:
            continue
        nodes = [
            {
                "id": str(snap.idx_to_meta[i][0]),
                "kind": snap.idx_to_meta[i][1],
                "name": snap.idx_to_meta[i][2],
            }
            for i in p
            if i in snap.idx_to_meta
        ]
        paths.append({"nodes": nodes, "length": len(p) - 1})
    return {"ok": True, "paths": paths}


ALL_RETRIEVAL_TOOLS = [
    universe_retrieve,
    get_graph_neighbors,
    explain_path,
    enrich_universe,
    get_career_pillars,
]
