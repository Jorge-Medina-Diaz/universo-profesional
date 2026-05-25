"""UniverseGraphService — write/read facade over the personal graph.

Sprint M scope:
  • upsert_entity / soft_delete_entity — mirror SQL entity rows into AGE
    vertices so downstream sprints have a populated graph to work with.
  • upsert_edge / expire_edge — typed edges with Graphiti-style
    `valid_from` / `valid_to`.
  • neighbors / get_node — light read helpers consumed by tests and the
    graph_router scaffold.

Sprints N+ extend this with: ESCO linking, signal materialisation,
episode tracking, community detection. The interface is intentionally
small so those extensions can layer on top.
"""
from __future__ import annotations

from collections.abc import Iterable
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from src.graph.domain import schema
from src.graph.infrastructure.age_client import cypher, parse_agtype

logger = structlog.get_logger(__name__)


def _now() -> datetime:
    return datetime.now(UTC)


def _iso(value: datetime | None) -> str | None:
    return value.isoformat() if value is not None else None


class UniverseGraphService:
    """Facade — write/read the personal graph in a session-scoped way.

    Every method takes the AsyncSession that the caller is already
    holding. The service does not own transactions; the caller commits.
    """

    # ------------------------------------------------------------------
    # Entity nodes
    # ------------------------------------------------------------------

    async def upsert_entity(
        self,
        session: AsyncSession,
        *,
        entity_id: UUID,
        user_id: UUID,
        kind: str,
        confidence: float | None = None,
        source: str = "manual",
        embedding: list[float] | None = None,
        esco_uri: str | None = None,
        extra: dict[str, Any] | None = None,
    ) -> None:
        """Create or update an :Entity vertex.

        The vertex is keyed by (id, user_id). We MERGE on id; the user_id
        is part of the merge pattern so two different users cannot
        accidentally collide.
        """
        now_iso = _iso(_now())
        # AGE has limited type coercion inside Cypher literals — strip
        # embedding to a stub property and store the full vector via the
        # mirror table when it matters for similarity. (Sprint N adds the
        # vector index over `ag_catalog._ag_label_vertex.properties->>'embedding_id'`.)
        embedding_present = embedding is not None and len(embedding) > 0
        params = {
            "id": str(entity_id),
            "user_id": str(user_id),
            "kind": kind,
            "confidence": confidence,
            "source": source,
            "esco_uri": esco_uri,
            "embedding_present": embedding_present,
            "extra": extra or {},
            "now": now_iso,
        }
        # Note: we intentionally do not push the embedding vector into
        # the agtype JSON property (it would be 1536 floats per node).
        # Sprint N introduces a sidecar `graph_entity_embeddings` table
        # keyed on (entity_id, user_id) for HNSW indexing.
        #
        # AGE 1.5.0-rc0 does not yet support MERGE … ON CREATE SET / ON
        # MATCH SET, so we use COALESCE on the "first-time" properties
        # (created_at, valid_from) and overwrite everything else.
        query = """
        MERGE (e:Entity {id: $id, user_id: $user_id})
        SET e.kind = $kind,
            e.created_at = COALESCE(e.created_at, $now),
            e.valid_from = COALESCE(e.valid_from, $now),
            e.updated_at = $now,
            e.confidence = $confidence,
            e.source = $source,
            e.esco_uri = $esco_uri,
            e.embedding_present = $embedding_present,
            e.extra = $extra,
            e.valid_to = NULL
        RETURN e
        """
        await cypher(session, schema.GRAPH_PERSONAL, query, params=params)

    async def soft_delete_entity(
        self,
        session: AsyncSession,
        *,
        entity_id: UUID,
        user_id: UUID,
    ) -> None:
        """Soft-delete: set valid_to=now() and expire all incident edges."""
        now_iso = _iso(_now())
        params = {"id": str(entity_id), "user_id": str(user_id), "now": now_iso}
        # Expire the vertex
        await cypher(
            session,
            schema.GRAPH_PERSONAL,
            """
            MATCH (e:Entity {id: $id, user_id: $user_id})
            SET e.valid_to = $now, e.updated_at = $now
            """,
            params=params,
        )
        # Expire incident edges
        await cypher(
            session,
            schema.GRAPH_PERSONAL,
            """
            MATCH (e:Entity {id: $id, user_id: $user_id})-[r]-()
            WHERE r.valid_to IS NULL
            SET r.valid_to = $now
            """,
            params=params,
        )

    # ------------------------------------------------------------------
    # Edges
    # ------------------------------------------------------------------

    async def upsert_edge(
        self,
        session: AsyncSession,
        *,
        edge_type: str,
        source_id: UUID,
        target_id: UUID,
        user_id: UUID,
        confidence: float | None = None,
        source: str = "manual",
        properties: dict[str, Any] | None = None,
    ) -> bool:
        """Create or revive a typed edge between two entity vertices.

        Idempotent: if an active edge of the same type already exists,
        we update its `updated_at` and merge `properties` rather than
        creating a duplicate. AGE does not enforce uniqueness, so we
        check via MATCH first.

        Returns True when the edge was written, False when one (or both)
        endpoints didn't exist (the MATCH found nothing) — callers can
        log the dangling reference instead of failing silently.
        """
        if not edge_type.isidentifier() or not edge_type.isupper():
            msg = f"edge_type must be an UPPER_SNAKE identifier: {edge_type!r}"
            raise ValueError(msg)

        now_iso = _iso(_now())
        params = {
            "src": str(source_id),
            "dst": str(target_id),
            "user_id": str(user_id),
            "confidence": confidence,
            "source": source,
            "properties": properties or {},
            "now": now_iso,
        }
        # Best-effort idempotency: find an active edge, otherwise create.
        # The edge_type is interpolated (it's a Cypher relationship type,
        # not a value), validated against an identifier regex above.
        # AGE 1.5.0 doesn't support MERGE … ON CREATE SET — use COALESCE.
        query = f"""
        MATCH (a:Entity {{id: $src, user_id: $user_id}}),
              (b:Entity {{id: $dst, user_id: $user_id}})
        MERGE (a)-[r:{edge_type}]->(b)
        SET r.created_at = COALESCE(r.created_at, $now),
            r.valid_from = COALESCE(r.valid_from, $now),
            r.updated_at = $now,
            r.valid_to = NULL,
            r.confidence = $confidence,
            r.source = $source,
            r.properties = $properties
        RETURN r
        """
        rows = await cypher(
            session, schema.GRAPH_PERSONAL, query, params=params, column_defs="r agtype"
        )
        if not rows:
            logger.warning(
                "graph_edge_endpoint_missing",
                edge_type=edge_type,
                source_id=str(source_id),
                target_id=str(target_id),
            )
            return False
        return True

    async def expire_edge(
        self,
        session: AsyncSession,
        *,
        edge_type: str,
        source_id: UUID,
        target_id: UUID,
        user_id: UUID,
    ) -> None:
        """Soft-expire an active edge (sets valid_to=now())."""
        if not edge_type.isidentifier() or not edge_type.isupper():
            msg = f"edge_type must be an UPPER_SNAKE identifier: {edge_type!r}"
            raise ValueError(msg)
        params = {
            "src": str(source_id),
            "dst": str(target_id),
            "user_id": str(user_id),
            "now": _iso(_now()),
        }
        query = f"""
        MATCH (a:Entity {{id: $src, user_id: $user_id}})-[r:{edge_type}]->
              (b:Entity {{id: $dst, user_id: $user_id}})
        WHERE r.valid_to IS NULL
        SET r.valid_to = $now
        """
        await cypher(session, schema.GRAPH_PERSONAL, query, params=params)

    async def invalidate_contradicting_edges(
        self,
        session: AsyncSession,
        *,
        edge_type: str,
        source_id: UUID,
        user_id: UUID,
        keep_target_id: UUID,
    ) -> None:
        """Expire active edges of a *single-valued* type from `source` to any
        target other than `keep_target_id`.

        Implements the Graphiti/Zep rule: a new single-valued fact
        *invalidates* the prior one (`valid_to = now`) rather than deleting
        it, so history is preserved and "true at time T" stays queryable.
        Call this just before `upsert_edge` for relations where a source may
        only point at one target at a time.
        """
        if not edge_type.isidentifier() or not edge_type.isupper():
            msg = f"edge_type must be an UPPER_SNAKE identifier: {edge_type!r}"
            raise ValueError(msg)
        params = {
            "src": str(source_id),
            "keep": str(keep_target_id),
            "user_id": str(user_id),
            "now": _iso(_now()),
        }
        query = f"""
        MATCH (a:Entity {{id: $src, user_id: $user_id}})-[r:{edge_type}]->
              (b:Entity {{user_id: $user_id}})
        WHERE r.valid_to IS NULL AND b.id <> $keep
        SET r.valid_to = $now
        """
        await cypher(session, schema.GRAPH_PERSONAL, query, params=params)

    # ------------------------------------------------------------------
    # Read helpers
    # ------------------------------------------------------------------

    async def get_entity(
        self,
        session: AsyncSession,
        *,
        entity_id: UUID,
        user_id: UUID,
    ) -> dict[str, Any] | None:
        rows = await cypher(
            session,
            schema.GRAPH_PERSONAL,
            "MATCH (e:Entity {id: $id, user_id: $user_id}) RETURN e",
            params={"id": str(entity_id), "user_id": str(user_id)},
            column_defs="e agtype",
        )
        if not rows:
            return None
        parsed = parse_agtype(rows[0]["e"])
        if isinstance(parsed, dict):
            return parsed.get("properties", parsed)
        return None

    async def neighbors(
        self,
        session: AsyncSession,
        *,
        entity_id: UUID,
        user_id: UUID,
        depth: int = 1,
        edge_kinds: Iterable[str] | None = None,
        include_expired: bool = False,
        limit: int = 500,
    ) -> list[dict[str, Any]]:
        """Return neighbouring nodes up to `depth` hops away.

        Only active edges (valid_to IS NULL) are followed unless
        `include_expired=True`. `edge_kinds` filters the relationship
        types — pass `None` for any. `limit` caps the result set so a
        dense graph at depth 4 can't blow up memory.
        """
        if depth < 1 or depth > 4:
            msg = "depth must be in [1, 4]"
            raise ValueError(msg)
        limit = max(1, min(limit, 2000))
        edge_filter = ""
        if edge_kinds:
            kinds = "|".join(
                k for k in edge_kinds if k.isidentifier() and k.isupper()
            )
            if kinds:
                edge_filter = f":{kinds}"
        active_filter = "" if include_expired else "WHERE ALL(r IN rels WHERE r.valid_to IS NULL)"
        query = f"""
        MATCH p = (e:Entity {{id: $id, user_id: $user_id}})
                  -[{edge_filter}*1..{depth}]-(n:Entity)
        WITH relationships(p) AS rels, n
        {active_filter}
        RETURN DISTINCT n
        LIMIT {limit}
        """
        rows = await cypher(
            session,
            schema.GRAPH_PERSONAL,
            query,
            params={"id": str(entity_id), "user_id": str(user_id)},
            column_defs="n agtype",
        )
        out: list[dict[str, Any]] = []
        for row in rows:
            parsed = parse_agtype(row["n"])
            if isinstance(parsed, dict):
                out.append(parsed.get("properties", parsed))
        return out


# Module-level singleton; cheap to share since it is stateless.
universe_graph_service = UniverseGraphService()
