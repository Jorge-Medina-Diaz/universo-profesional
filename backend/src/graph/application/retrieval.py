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
import math
import pickle
import time
from collections import OrderedDict, defaultdict
from collections.abc import Iterable
from dataclasses import dataclass, field
from typing import Any, Protocol
from uuid import NAMESPACE_URL, UUID, uuid5

import igraph as ig
import structlog
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.graph.domain import schema
from src.graph.domain.registry import GRAPH_REGISTRY
from src.graph.infrastructure.age_client import cypher, ensure_age_loaded
from src.shared.config import get_settings
from src.shared.embeddings import get_embeddings_service

logger = structlog.get_logger(__name__)


# ---------------------------------------------------------------------------
# Redis snapshot cache
# ---------------------------------------------------------------------------

_REDIS_TTL_SECONDS = 24 * 60 * 60  # 24h
_REDIS_KEY_PREFIX = "ppr:snapshot"
_redis_client: Any | None = None
_redis_lock: asyncio.Lock = asyncio.Lock()


async def _get_redis() -> Any | None:
    """Lazy singleton for redis.asyncio.Redis. Returns None if Redis is down."""
    global _redis_client
    if _redis_client is not None:
        return _redis_client
    async with _redis_lock:
        if _redis_client is not None:
            return _redis_client
        try:
            from redis.asyncio import Redis

            settings = get_settings()
            _redis_client = Redis.from_url(settings.redis_url, decode_responses=False)
            await _redis_client.ping()
        except Exception as exc:
            logger.warning("redis_snapshot_unavailable", error=str(exc))
            _redis_client = None
    return _redis_client


def _redis_key(user_id: UUID) -> str:
    return f"{_REDIS_KEY_PREFIX}:{user_id}"


async def _store_snapshot_redis(user_id: UUID, snapshot: _UserSnapshot) -> None:
    r = await _get_redis()
    if r is None:
        return
    try:
        payload = pickle.dumps(snapshot, protocol=pickle.HIGHEST_PROTOCOL)
        await r.setex(_redis_key(user_id), _REDIS_TTL_SECONDS, payload)
    except Exception as exc:
        logger.warning("redis_snapshot_store_failed", user_id=str(user_id), error=str(exc))


async def _load_snapshot_redis(user_id: UUID) -> _UserSnapshot | None:
    r = await _get_redis()
    if r is None:
        return None
    try:
        payload = await r.get(_redis_key(user_id))
        if payload is None:
            return None
        snapshot = pickle.loads(payload)
        if not isinstance(snapshot, _UserSnapshot):
            return None
        return snapshot
    except Exception as exc:
        logger.warning("redis_snapshot_load_failed", user_id=str(user_id), error=str(exc))
        return None


async def _delete_snapshot_redis(user_id: UUID) -> None:
    r = await _get_redis()
    if r is None:
        return
    try:
        await r.delete(_redis_key(user_id))
    except Exception as exc:
        logger.warning("redis_snapshot_delete_failed", user_id=str(user_id), error=str(exc))


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
    idx_to_esco: dict[int, str | None]  # idx → esco_uri
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
    await _delete_snapshot_redis(user_id)


async def _load_snapshot(
    session: AsyncSession, user_id: UUID
) -> _UserSnapshot:
    """Build (or fetch from LRU / Redis) the igraph snapshot of a user's graph."""
    async with _snapshots_lock:
        cached = _snapshots.get(user_id)
        if cached is not None:
            _snapshots.move_to_end(user_id)
            return cached

    # 1. Try Redis (cross-worker consistency).
    redis_snapshot = await _load_snapshot_redis(user_id)
    if redis_snapshot is not None:
        async with _snapshots_lock:
            _snapshots[user_id] = redis_snapshot
            _snapshots.move_to_end(user_id)
            while len(_snapshots) > _SNAPSHOT_LRU_MAX:
                _snapshots.popitem(last=False)
        return redis_snapshot

    await ensure_age_loaded(session)

    # Pull every active Entity vertex + every active edge from AGE for
    # this user. Edges live across many edge types — we use a single
    # MATCH with no type filter and capture the agtype label of each.
    vertex_rows = await cypher(
        session,
        schema.GRAPH_PERSONAL,
        """
        MATCH (e {user_id: $uid})
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
        MATCH (a {user_id: $uid})-[r]->(b {user_id: $uid})
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
    idx_to_esco: dict[int, str | None] = {}
    esco_by_id: dict[UUID, str | None] = {}
    for row in vertex_rows:
        entity_id = _coerce_uuid(parse_agtype(row.get("id")))
        esco_uri = parse_agtype(row.get("esco_uri"))
        if entity_id is not None:
            esco_by_id[entity_id] = esco_uri if isinstance(esco_uri, str) else None
    for entity_id, (kind, name) in names_by_id.items():
        idx = g.add_vertex(name=str(entity_id)).index
        id_to_idx[entity_id] = idx
        idx_to_meta[idx] = (entity_id, kind, name)
        idx_to_esco[idx] = esco_by_id.get(entity_id)

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
        idx_to_esco=idx_to_esco,
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
    # 2. Push to Redis so other workers see it.
    await _store_snapshot_redis(user_id, snapshot)
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
        # HippoRAG-style node specificity: weight each seed by INVERSE degree
        # so generic, highly-connected hubs (e.g. a ubiquitous skill) don't
        # dominate the random walk, while specific/rare seeds steer it.
        # s(node) = 1 / ln(e + degree)  →  1.0 at degree 0, decaying for hubs.
        # https://arxiv.org/abs/2405.14831
        personalization = [0.0] * snapshot.graph.vcount()
        weighted = 0
        for seed_id in seeds:
            idx = snapshot.id_to_idx.get(seed_id)
            if idx is not None:
                degree = snapshot.graph.degree(idx)
                personalization[idx] = 1.0 / math.log(math.e + degree)
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


# ---------------------------------------------------------------------------
# Community lane (4th lane — global / thematic retrieval)
# ---------------------------------------------------------------------------


class CommunityRetriever:
    name = "community"

    def __init__(self) -> None:
        self._embedder = get_embeddings_service()

    async def retrieve(
        self,
        session: AsyncSession,
        user_id: UUID,
        query: str,
        *,
        top_k: int = 12,
        kinds: Iterable[str] | None = None,
    ) -> list[ScoredItem]:
        try:
            embedding = await self._embedder.embed(query)
        except Exception as exc:
            logger.warning("community_retriever_embed_failed", error=str(exc))
            return []
        vec_literal = "[" + ",".join(f"{x:.7f}" for x in embedding) + "]"
        sql = (
            "SELECT community_id AS id, label, summary, "
            "1 - (embedding <=> CAST(:q AS vector)) AS score "
            "FROM community_summaries "
            "WHERE user_id = :uid "
            "  AND embedding IS NOT NULL "
            "ORDER BY embedding <=> CAST(:q AS vector) "
            "LIMIT :top_k"
        )
        rows = (
            await session.execute(
                text(sql),
                {"uid": str(user_id), "q": vec_literal, "top_k": top_k},
            )
        ).all()
        items: list[ScoredItem] = []
        for row in rows:
            # Communities are pseudo-entities: we synthesise a deterministic UUID
            # from the community_id string so downstream RRF treats them uniformly.
            pseudo_id = uuid5(NAMESPACE_URL, f"community:{row.id}")
            items.append(
                ScoredItem(
                    entity_id=pseudo_id,
                    kind="community",
                    name=str(row.label or ""),
                    score=float(row.score),
                    lane=self.name,
                    rationale=str(row.summary or ""),
                )
            )
        return _attach_ranks(items, lane=self.name)


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
    """Run BM25 + Dense + PPR + Community in parallel, fuse with RRF, then rerank.

    `kinds` filters all three entity lanes. None means every kind in
    GRAPH_REGISTRY. The community lane is always active (global/thematic
    retrieval). A cross-encoder/LLM reranker reorders the fused candidate
    pool against the query for a precision lift.
    """
    from src.shared.config import get_settings

    bm25 = BM25Retriever()
    dense = DenseRetriever()
    ppr = PPRRetriever()
    community = CommunityRetriever()

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
    community_res = await community.retrieve(
        session, user_id, query, top_k=per_lane_k
    )

    # Fuse a WIDER pool than top_k so the reranker has candidates to reorder.
    pool = max(top_k, get_settings().rerank_candidate_pool)
    fused = reciprocal_rank_fusion(
        [bm25_res, dense_res, ppr_res, community_res], k=k_rrf, top_k=pool
    )
    return await _rerank(query, fused, top_k=top_k)


async def _rerank(
    query: str, fused: list[HybridResult], *, top_k: int
) -> list[HybridResult]:
    """Reorder the fused pool with the configured reranker (best-effort)."""
    if len(fused) <= 1:
        return fused[:top_k]
    from src.graph.application.reranker import RerankCandidate, get_reranker

    reranker = get_reranker()
    candidates = [
        RerankCandidate(id=str(r.entity_id), text=f"{r.kind} · {r.name}") for r in fused
    ]
    try:
        ordered = await reranker.rerank(query, candidates, top_n=top_k)
    except Exception as exc:
        logger.warning("rerank_stage_failed", error=str(exc))
        return fused[:top_k]
    if not ordered:
        return fused[:top_k]

    by_id = {str(r.entity_id): r for r in fused}
    out: list[HybridResult] = []
    for rank, (cid, score) in enumerate(ordered, start=1):
        item = by_id.get(cid)
        if item is None:
            continue
        item.contributions["rerank"] = {"rank": float(rank), "score": round(score, 6)}
        out.append(item)
    return out[:top_k]


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
