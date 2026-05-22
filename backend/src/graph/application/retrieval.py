"""Hybrid retrieval — BM25 + dense + Personalized PageRank, fused with RRF.

Sprint O of the v2 plan. The retriever is the read side of the graph
universe: agents call `universe_retrieve(query=…)` and get a single
ranked list across every entity kind in the user's graph, mixing
keyword precision (BM25), semantic recall (pgvector), and structural
context (PPR over the personal graph).

Fusion is **Reciprocal Rank Fusion** with k=60 — the canonical default
from the literature (Cormack et al., Weaviate's recipe). RRF is
rank-based, robust to score scale differences across lanes, and
empirically delivers 15-30% recall lift over any single retriever.

Layout:
  • `ScoredItem`  — uniform shape returned by every lane.
  • `BM25Retriever` — Postgres tsvector + ts_rank_cd over the per-kind
    tables, scoped by user_id.
  • `DenseRetriever` — pgvector cosine over the per-kind embedding
    columns (mirrors the existing `PgVectorSemanticMatcher` so the two
    code paths stay aligned).
  • `PPRRetriever` — igraph snapshot per user, `personalized_pagerank`
    seeded by entity-linked terms. Snapshots are LRU-cached in process.
  • `reciprocal_rank_fusion` — pure function.
  • `hybrid_retrieve` — orchestrates the three lanes in parallel.

The retriever lives in `application/` because it's a use-case, not a
domain primitive. Adapters that need a different store (a future Neo4j
backbone, an OpenSearch BM25 lane) plug in via the simple `Retriever`
protocol.
"""
from __future__ import annotations

import asyncio
import time
from collections import OrderedDict, defaultdict
from collections.abc import Iterable
from dataclasses import dataclass, field
from typing import Any, Protocol
from uuid import UUID

import igraph as ig
import structlog
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.graph.domain import schema
from src.graph.domain.registry import GRAPH_REGISTRY
from src.graph.infrastructure.age_client import cypher, ensure_age_loaded
from src.shared.embeddings import get_embeddings_service

logger = structlog.get_logger(__name__)


# ---------------------------------------------------------------------------
# Shared types
# ---------------------------------------------------------------------------


@dataclass(slots=True)
class ScoredItem:
    """One ranked result from a single lane.

    `score` semantics differ per lane (BM25 ts_rank_cd, cosine, PPR mass),
    so it's only used for tie-breaking; the *rank* is what fusion uses.
    """

    entity_id: UUID
    kind: str
    name: str
    score: float
    rank: int = 0
    lane: str = ""
    rationale: str | None = None


@dataclass(slots=True)
class HybridResult:
    """Fused result with full provenance."""

    entity_id: UUID
    kind: str
    name: str
    fused_score: float
    contributions: dict[str, dict[str, float]] = field(default_factory=dict)
    """Map lane → {rank, score} for the lane's contribution. Useful for
    debugging and "why is this here?" UI surfaces."""


class Retriever(Protocol):
    name: str

    async def retrieve(
        self,
        session: AsyncSession,
        user_id: UUID,
        query: str,
        *,
        top_k: int,
        kinds: Iterable[str] | None = ...,
    ) -> list[ScoredItem]: ...


# ---------------------------------------------------------------------------
# BM25 lane
# ---------------------------------------------------------------------------


class BM25Retriever:
    name = "bm25"

    async def retrieve(
        self,
        session: AsyncSession,
        user_id: UUID,
        query: str,
        *,
        top_k: int = 30,
        kinds: Iterable[str] | None = None,
    ) -> list[ScoredItem]:
        kinds_list = list(kinds) if kinds else list(GRAPH_REGISTRY.keys())
        # asyncpg permits only one operation per connection at a time,
        # so per-kind queries run sequentially. The GIN(tsv) index keeps
        # each one ~3 ms, so 11 kinds = ~30 ms — well within budget.
        merged: list[ScoredItem] = []
        for kind in kinds_list:
            batch = await self._search_one_kind(
                session, user_id=user_id, kind=kind, query=query, top_k=top_k
            )
            merged.extend(batch)
        merged.sort(key=lambda x: x.score, reverse=True)
        return _attach_ranks(merged[:top_k], lane=self.name)

    async def _search_one_kind(
        self,
        session: AsyncSession,
        *,
        user_id: UUID,
        kind: str,
        query: str,
        top_k: int,
    ) -> list[ScoredItem]:
        cfg = GRAPH_REGISTRY.get(kind)
        if cfg is None:
            return []
        sql = (

            f"SELECT id::text AS id, {cfg.name_field} AS name, "
            f"ts_rank_cd(tsv, plainto_tsquery('spanish', :q)) AS score "
            f"FROM {cfg.sql_table} "
            f"WHERE user_id = :uid "
            f"  AND deleted_at IS NULL "
            f"  AND tsv @@ plainto_tsquery('spanish', :q) "
            f"ORDER BY score DESC LIMIT :top_k"
        )
        rows = (
            await session.execute(
                text(sql), {"uid": str(user_id), "q": query, "top_k": top_k}
            )
        ).all()
        return [
            ScoredItem(
                entity_id=UUID(row.id),
                kind=kind,
                name=str(row.name or ""),
                score=float(row.score or 0.0),
                lane=self.name,
            )
            for row in rows
        ]


# ---------------------------------------------------------------------------
# Dense lane
# ---------------------------------------------------------------------------


class DenseRetriever:
    name = "dense"

    def __init__(self) -> None:
        self._embedder = get_embeddings_service()

    async def retrieve(
        self,
        session: AsyncSession,
        user_id: UUID,
        query: str,
        *,
        top_k: int = 30,
        kinds: Iterable[str] | None = None,
    ) -> list[ScoredItem]:
        try:
            embedding = await self._embedder.embed(query)
        except Exception as exc:
            logger.warning("dense_retriever_embed_failed", error=str(exc))
            return []
        vec_literal = "[" + ",".join(f"{x:.7f}" for x in embedding) + "]"
        kinds_list = list(kinds) if kinds else list(GRAPH_REGISTRY.keys())

        # See BM25Retriever for the rationale on sequential per-kind queries.
        merged: list[ScoredItem] = []
        for kind in kinds_list:
            batch = await self._search_one_kind(
                session,
                user_id=user_id,
                kind=kind,
                vec_literal=vec_literal,
                top_k=top_k,
            )
            merged.extend(batch)
        merged.sort(key=lambda x: x.score, reverse=True)
        return _attach_ranks(merged[:top_k], lane=self.name)

    async def _search_one_kind(
        self,
        session: AsyncSession,
        *,
        user_id: UUID,
        kind: str,
        vec_literal: str,
        top_k: int,
    ) -> list[ScoredItem]:
        cfg = GRAPH_REGISTRY.get(kind)
        if cfg is None:
            return []
        if not await _table_has_column(session, cfg.sql_table, "embedding"):
            # Some kinds (artifact, architecture_decision in earlier
            # schemas) don't yet have an embedding column. The dense
            # lane just skips them — BM25 + PPR still cover the table.
            return []
        sql = (
            f"SELECT id::text AS id, {cfg.name_field} AS name, "
            f"1 - (embedding <=> CAST(:q AS vector)) AS score "
            f"FROM {cfg.sql_table} "
            f"WHERE user_id = :uid "
            f"  AND deleted_at IS NULL "
            f"  AND embedding IS NOT NULL "
            f"ORDER BY embedding <=> CAST(:q AS vector) "
            f"LIMIT :top_k"
        )
        rows = (
            await session.execute(
                text(sql),
                {"uid": str(user_id), "q": vec_literal, "top_k": top_k},
            )
        ).all()
        return [
            ScoredItem(
                entity_id=UUID(row.id),
                kind=kind,
                name=str(row.name or ""),
                score=float(row.score),
                lane=self.name,
            )
            for row in rows
        ]


# ---------------------------------------------------------------------------
# Personalized PageRank lane (igraph snapshot per user)
# ---------------------------------------------------------------------------


@dataclass
class _UserSnapshot:
    graph: Any  # igraph.Graph
    id_to_idx: dict[UUID, int]
    idx_to_meta: dict[int, tuple[UUID, str, str]]  # idx → (id, kind, name)
    built_at: float


_SNAPSHOT_LRU_MAX = 200
_snapshots: OrderedDict[UUID, _UserSnapshot] = OrderedDict()
# The LRU is mutated from many concurrent asyncio tasks (coherence
# writes invalidate, PPR queries load). Guard with a single lock — the
# critical sections are tiny so contention is negligible, and the lock
# prevents `popitem during iteration` races + lost-update on writes.
_snapshots_lock: asyncio.Lock = asyncio.Lock()


async def invalidate_snapshot(user_id: UUID) -> None:
    """Drop the cached snapshot. Called by event handlers after writes."""
    async with _snapshots_lock:
        _snapshots.pop(user_id, None)


async def _load_snapshot(
    session: AsyncSession, user_id: UUID
) -> _UserSnapshot:
    """Build (or fetch from LRU) the igraph snapshot of a user's graph."""
    async with _snapshots_lock:
        cached = _snapshots.get(user_id)
        if cached is not None:
            _snapshots.move_to_end(user_id)
            return cached

    await ensure_age_loaded(session)

    # Pull every active Entity vertex + every active edge from AGE for
    # this user. Edges live across many edge types — we use a single
    # MATCH with no type filter and capture the agtype label of each.
    vertex_rows = await cypher(
        session,
        schema.GRAPH_PERSONAL,
        """
        MATCH (e:Entity {user_id: $uid})
        WHERE e.valid_to IS NULL
        RETURN e.id, e.kind, e.esco_uri
        """,
        params={"uid": str(user_id)},
        column_defs="id agtype, kind agtype, esco_uri agtype",
    )
    edge_rows = await cypher(
        session,
        schema.GRAPH_PERSONAL,
        """
        MATCH (a:Entity {user_id: $uid})-[r]->(b:Entity {user_id: $uid})
        WHERE r.valid_to IS NULL
        RETURN a.id, b.id, type(r)
        """,
        params={"uid": str(user_id)},
        column_defs="a agtype, b agtype, t agtype",
    )

    # Hydrate names from the SQL tables — one query per kind keeps it
    # bounded by the number of entity kinds (11), not the graph size.
    names_by_id: dict[UUID, tuple[str, str]] = {}  # id → (kind, name)
    rows_by_kind: dict[str, set[UUID]] = defaultdict(set)
    for row in vertex_rows:
        from src.graph.infrastructure.age_client import parse_agtype

        entity_id = _coerce_uuid(parse_agtype(row.get("id")))
        kind = _strip_quotes(parse_agtype(row.get("kind")))
        if entity_id is None or not kind:
            continue
        rows_by_kind[kind].add(entity_id)
    for kind, ids in rows_by_kind.items():
        cfg = GRAPH_REGISTRY.get(kind)
        if cfg is None or not ids:
            continue
        sql = (
            f"SELECT id::text AS id, {cfg.name_field} AS name "
            f"FROM {cfg.sql_table} WHERE id = ANY(:ids)"
        )
        result = await session.execute(
            text(sql), {"ids": [str(i) for i in ids]}
        )
        for record in result.all():
            try:
                names_by_id[UUID(record.id)] = (kind, str(record.name or ""))
            except (ValueError, TypeError):
                continue

    # Build igraph.
    g = ig.Graph(directed=True)
    id_to_idx: dict[UUID, int] = {}
    idx_to_meta: dict[int, tuple[UUID, str, str]] = {}
    for entity_id, (kind, name) in names_by_id.items():
        idx = g.add_vertex(name=str(entity_id)).index
        id_to_idx[entity_id] = idx
        idx_to_meta[idx] = (entity_id, kind, name)

    for edge in edge_rows:
        from src.graph.infrastructure.age_client import parse_agtype

        src_id = _coerce_uuid(parse_agtype(edge.get("a")))
        dst_id = _coerce_uuid(parse_agtype(edge.get("b")))
        if src_id is None or dst_id is None:
            continue
        if src_id in id_to_idx and dst_id in id_to_idx:
            g.add_edge(id_to_idx[src_id], id_to_idx[dst_id])

    snapshot = _UserSnapshot(
        graph=g,
        id_to_idx=id_to_idx,
        idx_to_meta=idx_to_meta,
        built_at=time.time(),
    )
    # Insertion + eviction is the second critical section. Another task
    # may have raced ahead and built the same user's snapshot in parallel
    # — we overwrite with the fresher copy and trim the LRU tail.
    async with _snapshots_lock:
        _snapshots[user_id] = snapshot
        _snapshots.move_to_end(user_id)
        while len(_snapshots) > _SNAPSHOT_LRU_MAX:
            _snapshots.popitem(last=False)
    return snapshot


class PPRRetriever:
    name = "ppr"

    async def retrieve(
        self,
        session: AsyncSession,
        user_id: UUID,
        query: str,
        *,
        top_k: int = 30,
        kinds: Iterable[str] | None = None,
        seeds: list[UUID] | None = None,
    ) -> list[ScoredItem]:
        snapshot = await _load_snapshot(session, user_id)
        if snapshot.graph.vcount() == 0:
            return []
        # Seeds: either explicit (cross-lane coupling) or computed via
        # dense top-3 over the user's own entities. For Sprint O.4 the
        # orchestrator passes explicit seeds; for direct PPR queries we
        # fall back to dense.
        if seeds is None:
            seeds = await _pick_seeds_via_dense(session, user_id, query)
        if not seeds:
            return []
        personalization = [0.0] * snapshot.graph.vcount()
        weighted = 0
        for seed_id in seeds:
            idx = snapshot.id_to_idx.get(seed_id)
            if idx is not None:
                personalization[idx] = 1.0
                weighted += 1
        if weighted == 0:
            return []

        # igraph 0.11+ exposes `personalized_pagerank`; older releases
        # use `pagerank(reset=personalization)`. We try both.
        try:
            scores = snapshot.graph.personalized_pagerank(reset=personalization)
        except AttributeError:
            scores = snapshot.graph.pagerank(reset=personalization)

        items: list[ScoredItem] = []
        for idx, score in enumerate(scores):
            entity_id, kind, name = snapshot.idx_to_meta[idx]
            if kinds is not None and kind not in kinds:
                continue
            items.append(
                ScoredItem(
                    entity_id=entity_id,
                    kind=kind,
                    name=name,
                    score=float(score),
                    lane=self.name,
                )
            )
        items.sort(key=lambda x: x.score, reverse=True)
        # Exclude the seeds themselves — they're already known.
        seed_set = set(seeds)
        items = [i for i in items if i.entity_id not in seed_set]
        return _attach_ranks(items[:top_k], lane=self.name)


async def _pick_seeds_via_dense(
    session: AsyncSession, user_id: UUID, query: str
) -> list[UUID]:
    """Top-3 dense matches over the user's entities, used as PPR seeds."""
    retriever = DenseRetriever()
    hits = await retriever.retrieve(session, user_id, query, top_k=3)
    return [h.entity_id for h in hits if h.score > 0.5]


# ---------------------------------------------------------------------------
# Reciprocal Rank Fusion
# ---------------------------------------------------------------------------


def reciprocal_rank_fusion(
    rankings: list[list[ScoredItem]],
    *,
    k: int = 60,
    top_k: int = 12,
) -> list[HybridResult]:
    """RRF as in Cormack, Clarke & Buettcher (SIGIR 2009).

    For each candidate, score = Σ 1 / (k + rank_lane_i). k=60 is the
    canonical default and the value used by Weaviate, Vespa, OpenSearch
    out of the box.
    """
    aggregated: dict[UUID, HybridResult] = {}
    for ranking in rankings:
        if not ranking:
            continue
        lane_name = ranking[0].lane or "lane"
        for item in ranking:
            rank = item.rank or 0
            contribution = 1.0 / (k + rank) if rank else 0.0
            existing = aggregated.get(item.entity_id)
            if existing is None:
                existing = HybridResult(
                    entity_id=item.entity_id,
                    kind=item.kind,
                    name=item.name,
                    fused_score=0.0,
                )
                aggregated[item.entity_id] = existing
            existing.fused_score += contribution
            existing.contributions[lane_name] = {
                "rank": float(rank),
                "score": item.score,
            }
    out = sorted(aggregated.values(), key=lambda r: r.fused_score, reverse=True)
    return out[:top_k]


# ---------------------------------------------------------------------------
# Hybrid orchestrator
# ---------------------------------------------------------------------------


async def hybrid_retrieve(
    session: AsyncSession,
    user_id: UUID,
    query: str,
    *,
    top_k: int = 12,
    per_lane_k: int = 30,
    kinds: Iterable[str] | None = None,
    k_rrf: int = 60,
) -> list[HybridResult]:
    """Run BM25 + Dense + PPR in parallel and fuse with RRF.

    `kinds` filters all three lanes. None means every kind in
    GRAPH_REGISTRY.
    """
    bm25 = BM25Retriever()
    dense = DenseRetriever()
    ppr = PPRRetriever()

    # Lanes run sequentially because asyncpg only allows one operation
    # per connection. PPR piggybacks on the dense lane's top results for
    # seeding, so dense must run before PPR anyway.
    bm25_res = await bm25.retrieve(
        session, user_id, query, top_k=per_lane_k, kinds=kinds
    )
    dense_res = await dense.retrieve(
        session, user_id, query, top_k=per_lane_k, kinds=kinds
    )

    seeds = [item.entity_id for item in dense_res[:3] if item.score > 0.5]
    ppr_res = await ppr.retrieve(
        session, user_id, query, top_k=per_lane_k, kinds=kinds, seeds=seeds
    )

    fused = reciprocal_rank_fusion(
        [bm25_res, dense_res, ppr_res], k=k_rrf, top_k=top_k
    )
    return fused


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _attach_ranks(items: list[ScoredItem], *, lane: str) -> list[ScoredItem]:
    for rank, item in enumerate(items, start=1):
        item.rank = rank
        item.lane = lane
    return items


# Cache of (table_name, column_name) -> exists. Populated lazily on first
# query; valid for the process lifetime since schemas only change via
# Alembic migrations that restart the workers anyway.
_COLUMN_EXISTS_CACHE: dict[tuple[str, str], bool] = {}


async def _table_has_column(
    session: AsyncSession, table: str, column: str
) -> bool:
    cache_key = (table, column)
    cached = _COLUMN_EXISTS_CACHE.get(cache_key)
    if cached is not None:
        return cached
    row = (
        await session.execute(
            text(
                "SELECT 1 FROM information_schema.columns "
                "WHERE table_schema = 'public' "
                "  AND table_name = :t AND column_name = :c"
            ),
            {"t": table, "c": column},
        )
    ).first()
    exists = row is not None
    _COLUMN_EXISTS_CACHE[cache_key] = exists
    return exists


def _strip_quotes(value: Any) -> str:
    if value is None:
        return ""
    s = str(value)
    return s.strip('"')


def _coerce_uuid(value: Any) -> UUID | None:
    if value is None:
        return None
    try:
        return UUID(_strip_quotes(value))
    except (ValueError, TypeError):
        return None
