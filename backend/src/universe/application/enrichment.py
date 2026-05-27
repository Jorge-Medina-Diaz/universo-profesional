"""Agentic graph enrichment — infer relationships between universe entities.

The personal graph captures entities (skills, projects, experiences…) but the
*relationships* between them are mostly latent. This module is the autonomous
process that surfaces them, so the universe reads as a connected web instead of
disconnected dots.

It runs THROUGH the graph layer (honouring the coherence principle): every
inferred edge is written via ``universe_graph_service.upsert_edge`` with
``source="inferred"`` + a confidence + ``valid_from``, so it is tracked and
fully **refinable** (expireable / re-weightable) over time — never a silent,
permanent write.

Three kinds of inference:

  • **semantic** (``RELATED_TO``) — pgvector cosine kNN. Connects conceptually
    related entities even when they share no literal text (e.g. BM25 ↔ dense
    retrieval ↔ RAG). This is the main connective tissue for skill-heavy graphs.
  • **structural** (``USES_TECH``) — a project's ``tech_stack`` / an
    experience's ``competences`` resolved to existing Skill entities by name.
  • **structural** (``PART_OF``) — a project whose dates overlap an experience.

Missing embeddings are computed inline so every entity participates. The whole
pass is idempotent (MERGE-based edges) and safe to re-run.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import UTC, date, datetime
from typing import Any
from uuid import UUID

import structlog
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from src.graph.application.universe_graph import universe_graph_service
from src.graph.domain import schema
from src.graph.application.ports.age import cypher as age_cypher
from src.universe.application.ports.orm import ExperienceOrm, ProjectOrm, SkillOrm
from src.universe.application.ports.tasks import ENTITY_MAP as _ENTITY_MAP, refresh_embedding

logger = structlog.get_logger(__name__)


@dataclass
class EnrichmentStats:
    embeddings_computed: int = 0
    related_to: int = 0
    uses_tech: int = 0
    part_of: int = 0
    communities: int = 0

    def as_dict(self) -> dict[str, int]:
        return asdict(self)


def _norm(s: Any) -> str:
    return " ".join(str(s).lower().split())


def _vec(raw: Any) -> list[float] | None:
    """Coerce a pgvector column value (ndarray / list / str) to floats."""
    if raw is None:
        return None
    try:
        v = [float(x) for x in raw]
    except (TypeError, ValueError):
        return None
    return v or None


def _date_overlap(p: ProjectOrm, e: ExperienceOrm) -> bool:
    if p.start_date is None or e.start_date is None:
        return False
    today = date.today()
    p_end = p.end_date or (today if p.is_current else p.start_date)
    e_end = e.end_date or (today if e.is_current else e.start_date)
    return p.start_date <= e_end and e.start_date <= p_end


async def _ensure_embeddings(session: AsyncSession, user_id: UUID, stats: EnrichmentStats) -> None:
    """Compute embeddings for any entity missing one (separate session/commit)."""
    for kind, (orm_cls, _entity_cls) in _ENTITY_MAP.items():
        if not hasattr(orm_cls, "embedding"):
            continue
        ids = (
            await session.execute(
                select(orm_cls.id)
                .where(orm_cls.user_id == user_id)
                .where(orm_cls.deleted_at.is_(None))
                .where(orm_cls.embedding.is_(None))
            )
        ).scalars().all()
        for rid in ids:
            try:
                await refresh_embedding({}, entity_type=kind, entity_id=str(rid))
                stats.embeddings_computed += 1
            except Exception as exc:
                logger.warning("enrich_embed_failed", kind=kind, id=str(rid), error=str(exc))


async def enrich_user_graph(
    session: AsyncSession,
    user_id: UUID,
    *,
    knn: int = 4,
    min_score: float = 0.24,
    with_communities: bool = True,
) -> EnrichmentStats:
    """Infer + write relationships for the whole universe of one user.

    Idempotent. Returns counts of edges created/updated by type, plus the
    number of "career pillar" communities detected over the connected graph.
    """
    stats = EnrichmentStats()

    # 1. Backfill embeddings so every entity can participate in similarity.
    await _ensure_embeddings(session, user_id, stats)
    session.expire_all()

    # 2. Load entities, mirror each into an AGE vertex (so edges have endpoints),
    #    and collect vectors + structural material.
    recs: list[tuple[UUID, str, list[float]]] = []
    skills_by_norm: dict[str, UUID] = {}
    projects: list[ProjectOrm] = []
    experiences: list[ExperienceOrm] = []

    for kind, (orm_cls, _entity_cls) in _ENTITY_MAP.items():
        rows = (
            await session.execute(
                select(orm_cls)
                .where(orm_cls.user_id == user_id)
                .where(orm_cls.deleted_at.is_(None))
            )
        ).scalars().all()
        for r in rows:
            await universe_graph_service.upsert_entity(
                session, entity_id=r.id, user_id=user_id, kind=kind, source="seed"
            )
            v = _vec(getattr(r, "embedding", None))
            if v is not None:
                recs.append((r.id, kind, v))
            if isinstance(r, SkillOrm):
                skills_by_norm[_norm(r.name)] = r.id
            elif isinstance(r, ProjectOrm):
                projects.append(r)
            elif isinstance(r, ExperienceOrm):
                experiences.append(r)

    # 3+4. Structural edges (USES_TECH / PART_OF).
    await _infer_structural_edges(
        session, user_id, projects=projects, experiences=experiences,
        skills_by_norm=skills_by_norm, stats=stats,
    )

    # 5. Semantic RELATED_TO — cosine kNN web (undirected, deduped).
    await _infer_semantic_edges(session, user_id, recs=recs, knn=knn, min_score=min_score, stats=stats)

    # 6. Career pillars: detect + summarize communities over the now-connected
    #    graph (best-effort — never fails the enrichment if the LLM is down).
    if with_communities:
        try:
            from src.graph.application.communities import compute_communities

            pillars = await compute_communities(session, user_id)
            stats.communities = len(pillars)
        except Exception as exc:
            logger.warning("community_compute_failed", user_id=str(user_id), error=str(exc))

    logger.info("universe_enriched", user_id=str(user_id), **stats.as_dict())
    return stats


async def _infer_semantic_edges(
    session: AsyncSession,
    user_id: UUID,
    *,
    recs: list[tuple[UUID, str, list[float]]],
    knn: int,
    min_score: float,
    stats: EnrichmentStats,
) -> None:
    """HNSW-accelerated cosine-kNN RELATED_TO web with bi-temporal maintenance.

    Uses the pgvector HNSW index on `graph_entity_embeddings` so the kNN
    phase is O(N log N) instead of O(N²). Expire ALL prior inferred
    RELATED_TO first; the kNN MERGE below revives the ones still nearest
    (valid_to=NULL again), leaving genuinely-stale links expired.
    """
    await age_cypher(
        session,
        schema.GRAPH_PERSONAL,
        "MATCH (a {user_id: $uid})-[r:RELATED_TO]->(b {user_id: $uid}) "
        "WHERE r.valid_to IS NULL AND r.source = 'inferred' SET r.valid_to = $now",
        params={"uid": str(user_id), "now": datetime.now(UTC).isoformat()},
    )
    seen: set[tuple[str, str]] = set()
    for id_a, _ka, va in recs:
        vec_literal = "[" + ",".join(f"{x:.7f}" for x in va) + "]"
        rows = (
            await session.execute(
                text(
                    """
                    SELECT entity_id::text AS id,
                           1 - (embedding <=> CAST(:q AS vector)) AS score
                    FROM graph_entity_embeddings
                    WHERE user_id = :uid
                      AND entity_id <> :self_id
                      AND embedding IS NOT NULL
                    ORDER BY embedding <=> CAST(:q AS vector)
                    LIMIT :k
                    """
                ),
                {
                    "q": vec_literal,
                    "uid": str(user_id),
                    "self_id": str(id_a),
                    "k": knn * 2,  # over-fetch to survive min_score filter
                },
            )
        ).all()
        for row in rows:
            s = float(row.score or 0.0)
            if s < min_score:
                continue
            id_b = UUID(row.id)
            key = tuple(sorted((str(id_a), str(id_b))))
            if key in seen:
                continue
            seen.add(key)
            if await universe_graph_service.upsert_edge(
                session,
                edge_type=schema.RELATED_TO,
                source_id=UUID(key[0]),
                target_id=UUID(key[1]),
                user_id=user_id,
                source="inferred",
                confidence=round(s, 3),
                properties={"relation_label": "synonym" if s >= 0.8 else "similar"},
            ):
                stats.related_to += 1


async def _infer_structural_edges(
    session: AsyncSession,
    user_id: UUID,
    *,
    projects: list[ProjectOrm],
    experiences: list[ExperienceOrm],
    skills_by_norm: dict[str, UUID],
    stats: EnrichmentStats,
) -> None:
    """USES_TECH (tech_stack/competences → skill) + PART_OF (project↔experience)."""
    for p in projects:
        for tech in (p.tech_stack or []):
            sid = skills_by_norm.get(_norm(tech))
            if sid and await universe_graph_service.upsert_edge(
                session, edge_type=schema.USES_TECH, source_id=p.id, target_id=sid,
                user_id=user_id, source="inferred", confidence=0.9,
            ):
                stats.uses_tech += 1
    for e in experiences:
        for comp in (e.competences or []):
            sid = skills_by_norm.get(_norm(comp))
            if sid and await universe_graph_service.upsert_edge(
                session, edge_type=schema.USES_TECH, source_id=e.id, target_id=sid,
                user_id=user_id, source="inferred", confidence=0.85,
            ):
                stats.uses_tech += 1
    for p in projects:
        for e in experiences:
            if _date_overlap(p, e) and await universe_graph_service.upsert_edge(
                session, edge_type=schema.PART_OF, source_id=p.id, target_id=e.id,
                user_id=user_id, source="inferred", confidence=0.6,
            ):
                stats.part_of += 1


async def infer_for_entity(
    session: AsyncSession,
    *,
    user_id: UUID,
    entity_type: str,
    entity_id: UUID,
    payload: dict[str, Any],
) -> None:
    """Per-capture structural inference (cheap, runs inside post_upsert).

    Resolves a freshly-captured project/experience's tech_stack / competences
    to existing Skill entities → USES_TECH. Semantic RELATED_TO is left to the
    backfill / nightly pass, because a brand-new entity's embedding is computed
    asynchronously after commit.
    """
    techs: list[str] = []
    if entity_type == "project":
        techs = list(payload.get("tech_stack") or [])
    elif entity_type == "experience":
        techs = list(payload.get("competences") or [])
    if not techs:
        return

    wanted = {_norm(t) for t in techs if t}
    if not wanted:
        return
    rows = (
        await session.execute(
            select(SkillOrm.id, SkillOrm.name)
            .where(SkillOrm.user_id == user_id)
            .where(SkillOrm.deleted_at.is_(None))
        )
    ).all()
    by_norm = {_norm(name): sid for sid, name in rows}
    for key in wanted:
        sid = by_norm.get(key)
        if sid:
            await universe_graph_service.upsert_edge(
                session,
                edge_type=schema.USES_TECH,
                source_id=entity_id,
                target_id=sid,
                user_id=user_id,
                source="inferred",
                confidence=0.85,
            )
