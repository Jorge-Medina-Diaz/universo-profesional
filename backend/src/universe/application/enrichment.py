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

import math
from dataclasses import asdict, dataclass
from datetime import date
from typing import Any
from uuid import UUID

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.graph.application.universe_graph import universe_graph_service
from src.graph.domain import schema
from src.universe.infrastructure.orm import ExperienceOrm, ProjectOrm, SkillOrm
from src.universe.infrastructure.tasks import _ENTITY_MAP, refresh_embedding

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


def _cosine(a: list[float], b: list[float]) -> float:
    dot = 0.0
    na = 0.0
    nb = 0.0
    for x, y in zip(a, b):
        dot += x * y
        na += x * x
        nb += y * y
    if na <= 0.0 or nb <= 0.0:
        return 0.0
    return dot / (math.sqrt(na) * math.sqrt(nb))


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
            except Exception as exc:  # noqa: BLE001
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

    # 3. Structural USES_TECH — tech_stack / competences → Skill.
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

    # 4. Structural PART_OF — project nested in an overlapping experience.
    for p in projects:
        for e in experiences:
            if _date_overlap(p, e) and await universe_graph_service.upsert_edge(
                session, edge_type=schema.PART_OF, source_id=p.id, target_id=e.id,
                user_id=user_id, source="inferred", confidence=0.6,
            ):
                stats.part_of += 1

    # 5. Semantic RELATED_TO — cosine kNN web (undirected, deduped).
    seen: set[tuple[str, str]] = set()
    for i, (id_a, _ka, va) in enumerate(recs):
        sims: list[tuple[float, UUID]] = []
        for j, (id_b, _kb, vb) in enumerate(recs):
            if i == j:
                continue
            s = _cosine(va, vb)
            if s >= min_score:
                sims.append((s, id_b))
        sims.sort(key=lambda t: t[0], reverse=True)
        for s, id_b in sims[:knn]:
            key = tuple(sorted((str(id_a), str(id_b))))
            if key in seen:
                continue
            seen.add(key)
            # HippoRAG synonym edges: very-high cosine = near-duplicate concepts;
            # label them distinctly so retrieval can weight them as synonyms.
            relation_label = "synonym" if s >= 0.8 else "similar"
            if await universe_graph_service.upsert_edge(
                session,
                edge_type=schema.RELATED_TO,
                source_id=UUID(key[0]),
                target_id=UUID(key[1]),
                user_id=user_id,
                source="inferred",
                confidence=round(s, 3),
                properties={"relation_label": relation_label},
            ):
                stats.related_to += 1

    # 6. Career pillars: detect + summarize communities over the now-connected
    #    graph (best-effort — never fails the enrichment if the LLM is down).
    if with_communities:
        try:
            from src.graph.application.communities import compute_communities

            pillars = await compute_communities(session, user_id)
            stats.communities = len(pillars)
        except Exception as exc:  # noqa: BLE001
            logger.warning("community_compute_failed", user_id=str(user_id), error=str(exc))

    logger.info("universe_enriched", user_id=str(user_id), **stats.as_dict())
    return stats


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
