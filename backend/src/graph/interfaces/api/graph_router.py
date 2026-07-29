"""FastAPI router for graph operations.

Sprint M exposed minimal read endpoints. Sprint N adds quarantine and
edge mutation endpoints used by the chat HITL flows; Sprint O adds the
full retrieval surface (`/retrieve`, `/neighbors`, `/path`).
"""
from __future__ import annotations

from typing import Any, Literal
from uuid import UUID

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sqlalchemy import text

from src.coherence.application.coherence_v2 import resolve_quarantine
from src.graph.application.retrieval import hybrid_retrieve
from src.graph.application.universe_graph import universe_graph_service
from src.graph.domain import schema as graph_schema
from src.identity.interfaces.api.deps import CurrentUserId, SessionDep

# Cap on snapshot size — guards both server memory (igraph + Cypher
# result sets) and the JSON payload size pushed to the browser. A
# typical professional universe is well under 1 000 nodes; the cap
# lets us refuse the rare runaway case (data ingest gone wrong, a
# corrupted user) without crashing the process.
MAX_SNAPSHOT_NODES: int = 2000


router = APIRouter(prefix="/api/v1/graph", tags=["graph"])


# ---------------------------------------------------------------------------
# Read endpoints (Sprint M)
# ---------------------------------------------------------------------------


@router.get("/entity/{entity_id}")
async def get_entity(
    entity_id: UUID,
    user_id: CurrentUserId,
    session: SessionDep,
) -> dict[str, Any]:
    node = await universe_graph_service.get_entity(
        session, entity_id=entity_id, user_id=UUID(user_id)
    )
    if node is None:
        raise HTTPException(status_code=404, detail="entity not found in graph")
    return {"entity": node}


@router.get("/entity/{entity_id}/neighbors")
async def neighbors(
    entity_id: UUID,
    user_id: CurrentUserId,
    session: SessionDep,
    depth: int = 1,
    include_expired: bool = False,
) -> dict[str, Any]:
    nodes = await universe_graph_service.neighbors(
        session,
        entity_id=entity_id,
        user_id=UUID(user_id),
        depth=depth,
        include_expired=include_expired,
    )
    return {"items": nodes, "count": len(nodes)}


# ---------------------------------------------------------------------------
# Quarantine — Sprint N
# ---------------------------------------------------------------------------


@router.get("/quarantine")
async def list_quarantine(
    user_id: CurrentUserId,
    session: SessionDep,
    pending_only: bool = True,
    limit: int = 50,
) -> dict[str, Any]:
    sql = """
        SELECT id::text AS id, entity_id::text AS entity_id, kind, reason,
               candidates, notes, created_at, resolved_at, resolution
        FROM entity_quarantine
        WHERE user_id = :uid
    """
    if pending_only:
        sql += " AND resolved_at IS NULL"
    sql += " ORDER BY created_at DESC LIMIT :lim"
    rows = (
        await session.execute(text(sql), {"uid": user_id, "lim": limit})
    ).mappings().all()
    return {"items": [dict(r) for r in rows], "count": len(rows)}


class ResolveQuarantineRequest(BaseModel):
    chosen_uri: str | None = None
    resolution: str  # 'linked' | 'dismissed' | 'manual_note'


@router.post("/quarantine/{quarantine_id}/resolve")
async def resolve(
    quarantine_id: UUID,
    body: ResolveQuarantineRequest,
    user_id: CurrentUserId,
    session: SessionDep,
) -> dict[str, str]:
    await resolve_quarantine(
        session,
        quarantine_id=quarantine_id,
        user_id=UUID(user_id),
        chosen_uri=body.chosen_uri,
        resolution=body.resolution,
    )
    await session.commit()
    return {"status": "ok"}


# ---------------------------------------------------------------------------
# Edge mutations — Sprint N (HITL flows)
# ---------------------------------------------------------------------------


# Curated subset of graph_schema.PERSONAL_EDGE_TYPES that users may mutate via
# the HITL edge endpoint. System/provenance edges (EVIDENCES_SIGNAL,
# LINKS_TO_ESCO, TOUCHED_IN, MEMBER_OF) are intentionally excluded — those are
# written by the agent/ER pipeline, never by hand. Built from schema constants
# (not raw strings) so a renamed/removed type fails loudly at import.
_ALLOWED_EDGE_TYPES = {
    graph_schema.DEMONSTRATES,
    graph_schema.PART_OF,
    graph_schema.USES_TECH,
    graph_schema.OCCURRED_IN,
    graph_schema.PRODUCED,
    graph_schema.SUPERSEDES,
    graph_schema.DERIVED_FROM,
    graph_schema.RELATED_TO,
}
if not _ALLOWED_EDGE_TYPES <= graph_schema.PERSONAL_EDGE_TYPES:
    raise RuntimeError("HITL edge allowlist drifted from the ontology source of truth")


class EdgeMutationRequest(BaseModel):
    source_entity_id: UUID
    target_entity_id: UUID
    edge_type: str
    op: Literal["create", "expire"]
    confidence: float | None = None


@router.get("/snapshot")
async def snapshot(
    user_id: CurrentUserId,
    session: SessionDep,
    include_expired: bool = False,
) -> dict[str, Any]:
    """Return the user's personal graph in a sigma.js-friendly shape.

    Output (graphology serialization):
        {
          "nodes": [{"key": id, "attributes": {...}}],
          "edges": [{"key": id, "source": src, "target": dst, "attributes": {...}}],
        }

    Each node carries `kind`, `name`, `confidence`, `esco_uri` so the
    frontend can colour, size and label it without a second roundtrip.
    """
    from src.graph.application.retrieval import _load_snapshot

    snap = await _load_snapshot(session, UUID(user_id))
    if snap.graph.vcount() > MAX_SNAPSHOT_NODES:
        raise HTTPException(
            status_code=413,
            detail={
                "error": "snapshot_too_large",
                "node_count": snap.graph.vcount(),
                "max_nodes": MAX_SNAPSHOT_NODES,
                "hint": (
                    "Use /api/v1/graph/retrieve to fetch a focused subgraph "
                    "or filter by kind."
                ),
            },
        )

    # The igraph snapshot already has names + kinds; we re-format it as
    # graphology JSON. Edges are pulled fresh via a Cypher query to
    # include their typed labels.
    from src.graph.domain import schema as gschema
    from src.graph.infrastructure.age_client import cypher, parse_agtype
    from src.universe.application.area_keywords import primary_area
    from src.universe.application.shape_service import classify_entities_by_area

    # Per-entity semantic area (backend/frontend/cloud/ai_ml/…) drives the
    # frontend's clustered, colour-coded layout. Skills/projects/experiences
    # are classified from their full text; everything else falls back to a
    # name-only match (e.g. "AWS Certified …" → cloud).
    area_by_entity = await classify_entities_by_area(session, UUID(user_id))

    # Career-pillar (Leiden community) membership per entity, so the UI can
    # surface which pillar each node belongs to. Named edge var `m:` avoids
    # the SQLAlchemy `:TYPE` bind-param trap.
    pillar_by_entity: dict[str, str] = {}
    try:
        pillar_rows = await cypher(
            session,
            gschema.GRAPH_PERSONAL,
            """
            MATCH (e {user_id: $uid})-[m:MEMBER_OF]->
                  (c:Community {user_id: $uid})
            RETURN e.id, c.label
            """,
            params={"uid": user_id},
            column_defs="eid agtype, label agtype",
        )
        for row in pillar_rows:
            eid = _parse_agtype_str(row.get("eid"))
            label = _parse_agtype_str(row.get("label"))
            if eid and label:
                pillar_by_entity[eid] = label
    except Exception:
        pillar_by_entity = {}

    edge_rows = await cypher(
        session,
        gschema.GRAPH_PERSONAL,
        """
        MATCH (a {user_id: $uid})-[r]->(b {user_id: $uid})
        WHERE r.valid_to IS NULL OR $include_expired = true
        RETURN a.id, b.id, type(r), r.confidence
        """,
        params={
            "uid": user_id,
            "include_expired": bool(include_expired),
        },
        column_defs="src agtype, dst agtype, etype agtype, conf agtype",
    )

    nodes_out: list[dict[str, Any]] = []
    for idx in range(snap.graph.vcount()):
        meta = snap.idx_to_meta.get(idx)
        if not meta:
            continue
        entity_id, kind, name = meta
        area = area_by_entity.get(str(entity_id)) or primary_area(str(name).lower())
        esco_uri = snap.idx_to_esco.get(idx)
        nodes_out.append(
            {
                "key": str(entity_id),
                "attributes": {
                    "kind": kind,
                    "label": name,
                    "area": area,
                    "pillar": pillar_by_entity.get(str(entity_id)),
                    "esco_uri": esco_uri,
                },
            }
        )

    edges_out = []
    seen: set[tuple[str, str, str]] = set()
    for row in edge_rows:
        src_id = _parse_agtype_str(row.get("src"))
        dst_id = _parse_agtype_str(row.get("dst"))
        etype = _parse_agtype_str(row.get("etype"))
        conf = parse_agtype(row.get("conf"))
        if not src_id or not dst_id or not etype:
            continue
        key = (src_id, dst_id, etype)
        if key in seen:
            continue
        seen.add(key)
        edges_out.append(
            {
                "key": f"{src_id}::{etype}::{dst_id}",
                "source": src_id,
                "target": dst_id,
                "attributes": {
                    "edge_type": etype,
                    "confidence": conf,
                },
            }
        )

    return {
        "nodes": nodes_out,
        "edges": edges_out,
        "node_count": len(nodes_out),
        "edge_count": len(edges_out),
    }


def _parse_agtype_str(value: Any) -> str | None:
    from src.graph.infrastructure.age_client import parse_agtype

    parsed = parse_agtype(value)
    if parsed is None:
        return None
    return str(parsed).strip('"')


@router.get("/retrieve")
async def retrieve(
    q: str,
    user_id: CurrentUserId,
    session: SessionDep,
    top_k: int = 12,
    kinds: str | None = None,
) -> dict[str, Any]:
    """Hybrid retrieval (BM25 + dense + PPR + RRF) across the user's graph.

    `kinds` is a comma-separated allow-list (e.g. "skill,project"). Omit
    to search every entity kind.
    """
    kinds_list: list[str] | None = None
    if kinds:
        kinds_list = [k.strip() for k in kinds.split(",") if k.strip()]
    items = await hybrid_retrieve(
        session,
        UUID(user_id),
        q,
        top_k=top_k,
        kinds=kinds_list,
    )
    return {
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
        "count": len(items),
        "query": q,
    }


@router.post("/enrich")
async def enrich(
    user_id: CurrentUserId,
    session: SessionDep,
) -> dict[str, Any]:
    """Run agentic relationship enrichment over the user's whole universe.

    Infers semantic (RELATED_TO) + structural (USES_TECH/PART_OF) edges and
    writes them through the graph layer (source="inferred", refinable). Runs
    synchronously so the freshly-connected graph is visible immediately.
    """
    from src.universe.application.enrichment import enrich_user_graph

    stats = await enrich_user_graph(session, UUID(user_id))
    await session.commit()
    return {"status": "ok", "stats": stats.as_dict()}


@router.get("/communities")
async def communities(
    user_id: CurrentUserId,
    session: SessionDep,
) -> dict[str, Any]:
    """Return the user's "career pillars" — Leiden communities + LLM summaries."""
    from src.graph.application.communities import get_communities

    items = await get_communities(session, UUID(user_id))
    return {"items": items, "count": len(items)}


@router.post("/edges")
async def mutate_edge(
    body: EdgeMutationRequest,
    user_id: CurrentUserId,
    session: SessionDep,
) -> dict[str, str]:
    if body.edge_type not in _ALLOWED_EDGE_TYPES:
        raise HTTPException(
            status_code=400, detail=f"edge_type {body.edge_type!r} not allowed"
        )
    if body.op == "create":
        await universe_graph_service.upsert_edge(
            session,
            edge_type=body.edge_type,
            source_id=body.source_entity_id,
            target_id=body.target_entity_id,
            user_id=UUID(user_id),
            confidence=body.confidence,
            source="user",
        )
    else:
        await universe_graph_service.expire_edge(
            session,
            edge_type=body.edge_type,
            source_id=body.source_entity_id,
            target_id=body.target_entity_id,
            user_id=UUID(user_id),
        )
    await session.commit()
    return {"status": "ok"}
