"""Community detection — Leiden clusters over the personal graph = "career pillars".

GraphRAG and Zep/Graphiti build graph communities + LLM summaries to enable
*global / thematic* queries ("what's my professional narrative?", "what are my
strengths?") that entity-level retrieval can't answer. We run Leiden (Louvain
fallback) over the user's igraph snapshot, name each cluster with the LLM, and
persist `Community` vertices + `MEMBER_OF` edges (both already defined in
`schema.py`). Idempotent — recompute clears and rebuilds.

References: GraphRAG "Local to Global" (https://arxiv.org/html/2404.16130v2),
Zep (https://arxiv.org/abs/2501.13956).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import UUID

import structlog
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.graph.application.retrieval import _load_snapshot, invalidate_snapshot
from src.graph.domain import schema
from src.graph.infrastructure.age_client import cypher, parse_agtype
from src.shared.embeddings import get_embeddings_service
from src.shared.llm_client import get_llm_client

logger = structlog.get_logger(__name__)


@dataclass(slots=True)
class CareerPillar:
    id: str
    label: str
    summary: str
    members: list[dict[str, str]] = field(default_factory=list)

    @property
    def size(self) -> int:
        return len(self.members)


class _PillarSummary(BaseModel):
    label: str  # 2-4 word name for the cluster
    theme: str  # one-sentence description


async def _summarize(members: list[dict[str, str]]) -> tuple[str, str]:
    names = ", ".join(m["name"] for m in members if m.get("name"))
    fallback_label = (members[0]["name"] if members else "Pilar")[:48]
    fallback_summary = f"{len(members)} elementos relacionados de tu trayectoria."
    if not names:
        return fallback_label, fallback_summary
    llm = get_llm_client()
    try:
        result = await llm.structured(
            system=(
                "Eres un analista de carrera. Dado un grupo de entidades del "
                "universo profesional de una persona (skills, proyectos, "
                "experiencias…), nómbralo como un 'pilar' profesional. Devuelve "
                "JSON {label, theme}: label = 2-4 palabras en español; theme = "
                "una frase. No inventes datos que no estén en la lista."
            ),
            prompt=f"Entidades: {names}",
            schema=_PillarSummary,
            max_tokens=200,
            temperature=0.2,
        )
        label = (result.label or "").strip() or fallback_label
        theme = (result.theme or "").strip() or fallback_summary
        return label[:64], theme[:280]
    except Exception as exc:
        logger.warning("community_summary_failed", error=str(exc))
        return fallback_label, fallback_summary


async def compute_communities(
    session: AsyncSession,
    user_id: UUID,
    *,
    min_size: int = 2,
    max_members_for_llm: int = 24,
) -> list[CareerPillar]:
    """Detect communities on the user's graph, summarize, and persist them."""
    await invalidate_snapshot(user_id)
    snap = await _load_snapshot(session, user_id)
    g = snap.graph
    if g.vcount() < 3 or g.ecount() == 0:
        return []

    # Leiden needs an undirected graph; collapse parallel/RELATED_TO directions.
    undirected = g.as_undirected(mode="collapse")
    membership: list[int]
    try:
        membership = undirected.community_leiden(
            objective_function="modularity"
        ).membership
    except Exception:
        try:
            membership = undirected.community_multilevel().membership
        except Exception as exc:
            logger.warning("community_detection_failed", error=str(exc))
            return []

    groups: dict[int, list[int]] = {}
    for idx, comm in enumerate(membership):
        groups.setdefault(comm, []).append(idx)

    uid = str(user_id)
    now_iso = datetime.now(UTC).isoformat()

    # Clear previous communities (idempotent recompute).
    await cypher(
        session,
        schema.GRAPH_PERSONAL,
        f"MATCH (c:{schema.COMMUNITY} {{user_id: $uid}}) DETACH DELETE c",
        params={"uid": uid},
    )

    pillars: list[CareerPillar] = []
    for comm_idx, idxs in groups.items():
        if len(idxs) < min_size:
            continue
        members = [
            {
                "id": str(snap.idx_to_meta[i][0]),
                "kind": snap.idx_to_meta[i][1],
                "name": snap.idx_to_meta[i][2],
            }
            for i in idxs
            if i in snap.idx_to_meta
        ]
        if len(members) < min_size:
            continue
        label, summary = await _summarize(members[:max_members_for_llm])
        cid = f"comm-{uid}-{comm_idx}"
        await cypher(
            session,
            schema.GRAPH_PERSONAL,
            f"""
            MERGE (c:{schema.COMMUNITY} {{id: $cid, user_id: $uid}})
            SET c.label = $label, c.summary = $summary, c.size = $size,
                c.member_names = $names, c.updated_at = $now
            """,
            params={
                "cid": cid,
                "uid": uid,
                "label": label,
                "summary": summary,
                "size": len(members),
                "names": " · ".join(m["name"] for m in members),
                "now": now_iso,
            },
        )
        for m in members:
            await cypher(
                session,
                schema.GRAPH_PERSONAL,
                f"""
                MATCH (e {{id: $eid, user_id: $uid}}),
                      (c:{schema.COMMUNITY} {{id: $cid, user_id: $uid}})
                MERGE (e)-[m:{schema.MEMBER_OF}]->(c)
                """,
                params={"eid": m["id"], "uid": uid, "cid": cid},
            )
        pillars.append(CareerPillar(id=cid, label=label, summary=summary, members=members))

    # Persist relational sidecar with embedding (4th retrieval lane).
    await _persist_summaries(session, user_id, pillars)

    pillars.sort(key=lambda p: p.size, reverse=True)
    logger.info("communities_computed", user_id=uid, count=len(pillars))
    return pillars


async def _persist_summaries(
    session: AsyncSession, user_id: UUID, pillars: list[CareerPillar]
) -> None:
    """Upsert community_summaries rows with embeddings for vector retrieval."""
    if not pillars:
        return
    # Clear stale rows for this user.
    await session.execute(
        text("DELETE FROM community_summaries WHERE user_id = :uid"),
        {"uid": str(user_id)},
    )
    embedder = get_embeddings_service()
    for p in pillars:
        embed_text = f"{p.label}. {p.summary}"
        try:
            vec = await embedder.embed(embed_text)
        except Exception as exc:
            logger.warning("community_embed_failed", community_id=p.id, error=str(exc))
            vec = None
        vec_literal = None
        if vec is not None:
            vec_literal = "[" + ",".join(f"{x:.7f}" for x in vec) + "]"
        member_ids = [UUID(m["id"]) for m in p.members if m.get("id")]
        await session.execute(
            text(
                """
                INSERT INTO community_summaries (
                    user_id, community_id, label, summary, member_ids, embedding, updated_at
                ) VALUES (
                    :uid, :cid, :label, :summary, :mids,
                    CAST(:vec AS vector), now()
                )
                """
            ),
            {
                "uid": str(user_id),
                "cid": p.id,
                "label": p.label,
                "summary": p.summary,
                "mids": member_ids,
                "vec": vec_literal,
            },
        )


async def get_communities(session: AsyncSession, user_id: UUID) -> list[dict]:
    """Read persisted career pillars for a user."""
    rows = await cypher(
        session,
        schema.GRAPH_PERSONAL,
        f"""
        MATCH (c:{schema.COMMUNITY} {{user_id: $uid}})
        RETURN c.id, c.label, c.summary, c.size, c.member_names
        """,
        params={"uid": str(user_id)},
        column_defs="id agtype, label agtype, summary agtype, size agtype, names agtype",
    )
    out: list[dict] = []
    for r in rows:
        names = parse_agtype(r.get("names"))
        out.append(
            {
                "id": _s(parse_agtype(r.get("id"))),
                "label": _s(parse_agtype(r.get("label"))),
                "summary": _s(parse_agtype(r.get("summary"))),
                "size": int(parse_agtype(r.get("size")) or 0),
                "members": _s(names).split(" · ") if names else [],
            }
        )
    out.sort(key=lambda c: c["size"], reverse=True)
    return out


def _s(value: object) -> str:
    if value is None:
        return ""
    return str(value).strip('"')
