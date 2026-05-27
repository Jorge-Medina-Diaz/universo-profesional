from __future__ import annotations

import asyncio
import pickle
import time
from collections import OrderedDict, defaultdict
from dataclasses import dataclass
from typing import Any
from uuid import UUID

import igraph as ig
import structlog
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.graph.application.retrieval._helpers import _coerce_uuid, _strip_quotes
from src.graph.domain import schema
from src.graph.domain.registry import GRAPH_REGISTRY
from src.graph.infrastructure.age_client import cypher, ensure_age_loaded
from src.shared.config import get_settings

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
