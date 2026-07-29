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

from src.graph.application.ports import GraphRepository
from src.graph.domain import schema

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

    @property
    def _repo(self) -> Any:
        """The wired repository, or a clear error naming what is missing.

        `_graph_repo` is Optional because it is injected after construction;
        without this guard every call site was a union-attr error and a latent
        `AttributeError: 'NoneType' has no attribute 'execute'`.
        """
        if self._graph_repo is None:
            raise RuntimeError("UniverseGraphService has no graph repository wired")
        return self._graph_repo

    def __init__(self, graph_repo: GraphRepository | None = None) -> None:
        """Inject a ``GraphRepository`` adapter.

        When *graph_repo* is omitted a default AGE adapter is loaded
        lazily so the module-level singleton keeps working for legacy
        callers while new code can inject a mock or alternate backend.
        """
        if graph_repo is None:
            from src.graph.application.ports.age import age_graph_repository

            graph_repo = age_graph_repository
        self._graph_repo = graph_repo

    # ------------------------------------------------------------------
    # Low-level query execution (used by enrichment + discovery tools)
    # ------------------------------------------------------------------

    async def _execute_cypher(
        self,
        session: AsyncSession,
        query: str,
        params: dict[str, Any] | None = None,
        *,
        graph: str = schema.GRAPH_PERSONAL,
        column_defs: str = "result agtype",
    ) -> list[dict[str, Any]]:
        """Run a raw Cypher query through the graph repository."""
        return await self._repo.execute(session, graph, query, params=params, column_defs=column_defs)

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
        """Create or update a typed vertex.

        Sprint R upgrades the graph from a single :Entity label to typed
        labels (:Experience, :Skill, …).  The label is derived from *kind*
        via KIND_TO_LABEL; if the kind is not yet mapped we fall back to
        :Entity so the write never fails.
        """
        label = schema.KIND_TO_LABEL.get(kind, schema.ENTITY)
        now_iso = _iso(_now())
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
        # AGE 1.5 does not support MERGE … ON CREATE SET / ON MATCH SET,
        # so we COALESCE the immutable-first properties.
        query = f"""
        MERGE (e:{label} {{id: $id, user_id: $user_id}})
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
        await self._repo.execute(session, schema.GRAPH_PERSONAL, query, params=params)

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
        # Expire the vertex — we don't know the label, so use the generic
        # :Entity fallback (still present for legacy nodes).
        await self._repo.execute(
            session,
            schema.GRAPH_PERSONAL,
            """
            MATCH (e {id: $id, user_id: $user_id})
            SET e.valid_to = $now, e.updated_at = $now
            """,
            params=params,
        )
        # Expire incident edges
        await self._repo.execute(
            session,
            schema.GRAPH_PERSONAL,
            """
            MATCH (e {id: $id, user_id: $user_id})-[r]-()
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
        if edge_type not in schema.PERSONAL_EDGE_TYPES:
            msg = f"unknown personal edge_type (not in ontology allowlist): {edge_type!r}"
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
        # not a value), validated against the ontology allowlist above.
        #
        # TWO statements, deliberately. AGE 1.5 silently DROPS a `SET` that
        # follows a `MERGE` which *creates* a relationship: the edge lands with
        # `properties: {}` and no error. Node MERGE is unaffected, which is why
        # this hid for so long — vertices always looked right. An edge born
        # without `source`/`valid_from` is invisible to every maintenance pass
        # that filters on them (notably the enrichment expiry, which matches
        # `r.source = 'inferred'`), so stale inferred edges could never expire.
        # Splitting it means the second statement MATCHes an edge that already
        # exists, where SET does persist.
        # AGE 1.5.0 also lacks MERGE … ON CREATE SET — hence the COALESCEs.
        merge_query = f"""
        MATCH (a {{id: $src, user_id: $user_id}}),
              (b {{id: $dst, user_id: $user_id}})
        MERGE (a)-[r:{edge_type}]->(b)
        RETURN r
        """
        rows = await self._repo.execute(
            session, schema.GRAPH_PERSONAL, merge_query, params=params, column_defs="r agtype"
        )
        if not rows:
            logger.warning(
                "graph_edge_endpoint_missing",
                edge_type=edge_type,
                source_id=str(source_id),
                target_id=str(target_id),
            )
            return False

        set_query = f"""
        MATCH (a {{id: $src, user_id: $user_id}})-[r:{edge_type}]->
              (b {{id: $dst, user_id: $user_id}})
        SET r.created_at = COALESCE(r.created_at, $now),
            r.valid_from = COALESCE(r.valid_from, $now),
            r.updated_at = $now,
            r.valid_to = NULL,
            r.confidence = $confidence,
            r.source = $source,
            r.properties = $properties
        RETURN r
        """
        await self._repo.execute(
            session, schema.GRAPH_PERSONAL, set_query, params=params, column_defs="r agtype"
        )
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
        if edge_type not in schema.PERSONAL_EDGE_TYPES:
            msg = f"unknown personal edge_type (not in ontology allowlist): {edge_type!r}"
            raise ValueError(msg)
        params = {
            "src": str(source_id),
            "dst": str(target_id),
            "user_id": str(user_id),
            "now": _iso(_now()),
        }
        query = f"""
        MATCH (a {{id: $src, user_id: $user_id}})-[r:{edge_type}]->
              (b {{id: $dst, user_id: $user_id}})
        WHERE r.valid_to IS NULL
        SET r.valid_to = $now
        """
        await self._repo.execute(session, schema.GRAPH_PERSONAL, query, params=params)

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
        if edge_type not in schema.PERSONAL_EDGE_TYPES:
            msg = f"unknown personal edge_type (not in ontology allowlist): {edge_type!r}"
            raise ValueError(msg)
        params = {
            "src": str(source_id),
            "keep": str(keep_target_id),
            "user_id": str(user_id),
            "now": _iso(_now()),
        }
        query = f"""
        MATCH (a {{id: $src, user_id: $user_id}})-[r:{edge_type}]->
              (b {{user_id: $user_id}})
        WHERE r.valid_to IS NULL AND b.id <> $keep
        SET r.valid_to = $now
        """
        await self._repo.execute(session, schema.GRAPH_PERSONAL, query, params=params)

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
        """Read a vertex by id, matching any label (typed or legacy :Entity)."""
        rows = await self._repo.execute(
            session,
            schema.GRAPH_PERSONAL,
            "MATCH (e {id: $id, user_id: $user_id}) RETURN e",
            params={"id": str(entity_id), "user_id": str(user_id)},
            column_defs="e agtype",
        )
        if not rows:
            return None
        parsed = self._graph_repo.parse_result(rows[0]["e"])
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
        edge_kinds_list = (
            [k for k in edge_kinds if k.isidentifier() and k.isupper()]
            if edge_kinds
            else []
        )
        params = {"id": str(entity_id), "user_id": str(user_id)}

        # AGE 1.5 does NOT support `relationships(p)` / `ALL(...)` over a
        # variable-length path (raises "syntax error at or near ("). So:
        #  • depth 1 → direct pattern with a named edge var (lets us filter
        #    active edges, and keeps the colon off `[` so SQLAlchemy's text()
        #    doesn't mistake `:TYPE` for a bind param).
        #  • depth >1 → variable-length over NODES, filtering the neighbour's
        #    own validity (per-edge expiry can't be checked in AGE here).
        if depth == 1:
            edge_filter = f":{'|'.join(edge_kinds_list)}" if edge_kinds_list else ""
            edge_active = "" if include_expired else "WHERE r.valid_to IS NULL"
            query = f"""
            MATCH (e {{id: $id, user_id: $user_id}})
                  -[r{edge_filter}]-(n {{user_id: $user_id}})
            {edge_active}
            RETURN DISTINCT n
            LIMIT {limit}
            """
        else:
            node_active = "" if include_expired else "WHERE n.valid_to IS NULL"
            query = f"""
            MATCH (e {{id: $id, user_id: $user_id}})
                  -[*1..{depth}]-(n {{user_id: $user_id}})
            {node_active}
            RETURN DISTINCT n
            LIMIT {limit}
            """
        rows = await self._repo.execute(
            session,
            schema.GRAPH_PERSONAL,
            query,
            params=params,
            column_defs="n agtype",
        )
        out: list[dict[str, Any]] = []
        for row in rows:
            parsed = self._graph_repo.parse_result(row["n"])
            if isinstance(parsed, dict):
                out.append(parsed.get("properties", parsed))
        return out


# Module-level singleton; cheap to share since it is stateless.
# The default adapter is loaded lazily inside the class so the
# application layer does not import infrastructure at import time.
universe_graph_service = UniverseGraphService()
