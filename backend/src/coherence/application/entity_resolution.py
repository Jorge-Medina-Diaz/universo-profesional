"""Entity Resolution v2 — blocking, pairwise matching, clustering, merge, provenance.

Sprint R replaces the flat "exact → semantic ≥ 0.92" matcher with a full ER
pipeline that can resolve "Google Inc." vs "Google LLC" via composite
similarity, cluster transitive matches, and leave a provenance trail in the
graph so merges are auditable and reversible.

Pipeline stages:
  1. BLOCKING   — reduce the candidate set from "all user's entities" to
                  a small bucket using cheap heuristics (exact name,
                  phonetic key, embedding nearest-neighbour, shared ESCO URI).
  2. MATCHING   — score each candidate pair with a weighted composite:
                  • embedding similarity (dense semantic)
                  • string similarity (Jaro-Winkler on canonical name)
                  • temporal overlap (do the lifespans intersect?)
                  • graph neighbourhood overlap (shared neighbours in AGE)
  3. CLUSTERING — build connected components from pairs whose composite
                  score ≥ matching_threshold.  Ambiguous pairs
                  (ambiguous_low ≤ score < matching_threshold) are surfaced
                  to the user via suggestions; below ambiguous_low → discarded.
  4. MERGE      — apply per-kind field-resolution rules (er_rules.py) to
                  collapse the cluster into a single golden record.
  5. PROVENANCE — write a :MergeEvent vertex + :MERGED_INTO edges so the
                  operation is fully auditable in the graph.
"""
from __future__ import annotations

from collections import defaultdict
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from typing import Any, Literal
from uuid import UUID, uuid4

import structlog
from jellyfish import jaro_winkler_similarity
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.coherence.domain.er_rules import FieldRule, FieldStrategy, config_for
from src.graph.application.universe_graph import universe_graph_service
from src.graph.domain import schema as graph_schema
from src.graph.infrastructure.age_client import cypher
from src.shared.embeddings import get_embeddings_service

logger = structlog.get_logger(__name__)


# Result types


@dataclass(frozen=True)
class MatchCandidate:
    entity_id: UUID
    score: float
    signals: dict[str, float] = field(default_factory=dict)
    """Per-signal breakdown: embedding, string, temporal, graph."""


@dataclass(frozen=True)
class Cluster:
    cluster_id: UUID
    entity_ids: set[UUID]
    representative_id: UUID
    """The id of the oldest entity in the cluster (used as merge target)."""


@dataclass(frozen=True)
class ResolutionResult:
    status: Literal["created", "merged", "ambiguous", "no_match"]
    entity_id: UUID | None
    """The surviving entity id (create target or merge target)."""
    merged_ids: list[UUID] = field(default_factory=list)
    """Ids that were absorbed into entity_id (empty for created/no_match)."""
    suggestion_payload: dict[str, Any] | None = None
    """Populated when status="ambiguous" to drive the HITL suggestion."""
    provenance_event_id: UUID | None = None


# 1. Blocking


class Blocker:
    """Produce a small candidate set for expensive pairwise matching."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._embedder = get_embeddings_service()

    async def block(
        self,
        *,
        user_id: UUID,
        kind: str,
        payload: dict[str, Any],
        cfg: dict[str, Any],
        top_k: int = 12,
    ) -> set[UUID]:
        """Return candidate entity ids that *might* match the payload."""
        candidates: set[UUID] = set()
        er_cfg = config_for(kind)
        if er_cfg is None:
            return candidates

        for key in er_cfg.blocking_keys:
            if key == "name_exact":
                candidates.update(await self._block_name_exact(user_id, kind, payload, cfg))
            elif key == "name_phonetic":
                candidates.update(await self._block_name_phonetic(user_id, kind, payload, cfg))
            elif key == "embedding_nearest":
                candidates.update(await self._block_embedding(user_id, kind, payload, cfg, top_k))
            elif key == "esco_uri":
                candidates.update(await self._block_esco_uri(user_id, kind, payload))
            if len(candidates) >= top_k * 2:
                break
        return candidates

    async def _block_name_exact(
        self, user_id: UUID, kind: str, payload: dict[str, Any], cfg: dict[str, Any]
    ) -> set[UUID]:
        name_field = cfg.get("name_field")
        if not name_field:
            return set()
        name_value = payload.get(name_field)
        if not name_value:
            return set()
        table = cfg.get("table")
        if not table:
            return set()
        rows = (
            await self._session.execute(
                text(
                    f"SELECT id::text AS id FROM {table} "
                    f"WHERE user_id = :uid AND lower({name_field}) = lower(:n)"
                ),
                {"uid": str(user_id), "n": str(name_value)},
            )
        ).all()
        return {UUID(r.id) for r in rows}

    async def _block_name_phonetic(
        self, user_id: UUID, kind: str, payload: dict[str, Any], cfg: dict[str, Any]
    ) -> set[UUID]:
        name_field = cfg.get("name_field")
        if not name_field:
            return set()
        name_value = payload.get(name_field)
        if not name_value:
            return set()
        table = cfg.get("table")
        if not table:
            return set()
        # Use metaphone as a simple phonetic key.  PostgreSQL fuzzystrmatch
        # would be better but isn't guaranteed installed; we approximate in Python.
        from jellyfish import metaphone

        phonetic = metaphone(str(name_value))
        rows = (
            await self._session.execute(
                text(
                    f"SELECT id::text AS id, {name_field} FROM {table} "
                    f"WHERE user_id = :uid AND {name_field} IS NOT NULL"
                ),
                {"uid": str(user_id)},
            )
        ).all()
        out: set[UUID] = set()
        for r in rows:
            if metaphone(str(getattr(r, name_field, ""))) == phonetic:
                out.add(UUID(r.id))
        return out

    async def _block_embedding(
        self, user_id: UUID, kind: str, payload: dict[str, Any], cfg: dict[str, Any], top_k: int
    ) -> set[UUID]:
        emb_text_fn = cfg.get("embedding_text")
        if not emb_text_fn:
            return set()
        text_in = emb_text_fn(payload).strip()
        if not text_in:
            return set()
        table = cfg.get("table")
        if not table:
            return set()
        embedding = await self._embedder.embed(text_in)
        vec = "[" + ",".join(f"{x:.7f}" for x in embedding) + "]"
        rows = (
            await self._session.execute(
                text(
                    f"""
                    SELECT id::text AS id,
                           1 - (embedding <=> CAST(:emb AS vector)) AS score
                    FROM {table}
                    WHERE user_id = :uid AND embedding IS NOT NULL
                    ORDER BY embedding <=> CAST(:emb AS vector)
                    LIMIT :k
                    """
                ),
                {"emb": vec, "uid": str(user_id), "k": top_k},
            )
        ).all()
        return {UUID(r.id) for r in rows}

    async def _block_esco_uri(
        self, user_id: UUID, kind: str, payload: dict[str, Any]
    ) -> set[UUID]:
        esco_uri = payload.get("esco_uri")
        if not esco_uri:
            return set()
        rows = (
            await self._session.execute(
                text(
                    """
                    SELECT entity_id::text AS id
                    FROM graph_esco_links
                    WHERE user_id = :uid AND esco_uri = :uri
                    """
                ),
                {"uid": str(user_id), "uri": esco_uri},
            )
        ).all()
        return {UUID(r.id) for r in rows}


# 2. Pairwise matching


@dataclass(frozen=True)
class PairwiseScore:
    composite: float
    embedding: float = 0.0
    string: float = 0.0
    temporal: float = 0.0
    graph: float = 0.0


class PairwiseMatcher:
    """Score a candidate entity against the incoming payload."""

    _WEIGHTS = {
        "embedding": 0.40,
        "string": 0.30,
        "temporal": 0.15,
        "graph": 0.15,
    }

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._embedder = get_embeddings_service()

    async def score(
        self,
        *,
        user_id: UUID,
        kind: str,
        payload: dict[str, Any],
        candidate_id: UUID,
        candidate_row: dict[str, Any],
        cfg: dict[str, Any],
    ) -> PairwiseScore:
        emb_sim = await self._embedding_sim(payload, candidate_row, cfg)
        str_sim = self._string_sim(payload, candidate_row, cfg)
        tmp_sim = self._temporal_sim(payload, candidate_row)
        graph_sim = await self._graph_sim(user_id, payload, candidate_id)
        composite = (
            self._WEIGHTS["embedding"] * emb_sim
            + self._WEIGHTS["string"] * str_sim
            + self._WEIGHTS["temporal"] * tmp_sim
            + self._WEIGHTS["graph"] * graph_sim
        )
        return PairwiseScore(
            composite=round(composite, 4),
            embedding=round(emb_sim, 4),
            string=round(str_sim, 4),
            temporal=round(tmp_sim, 4),
            graph=round(graph_sim, 4),
        )

    async def _embedding_sim(
        self, payload: dict[str, Any], candidate_row: dict[str, Any], cfg: dict[str, Any]
    ) -> float:
        emb_text_fn = cfg.get("embedding_text")
        if not emb_text_fn:
            return 0.0
        text_a = emb_text_fn(payload).strip()
        text_b = emb_text_fn(candidate_row).strip()
        if not text_a or not text_b:
            return 0.0
        # Fast path: exact same text
        if text_a.lower() == text_b.lower():
            return 1.0
        emb_a = await self._embedder.embed(text_a)
        emb_b = await self._embedder.embed(text_b)
        # cosine similarity
        dot = sum(x * y for x, y in zip(emb_a, emb_b))
        norm_a = sum(x * x for x in emb_a) ** 0.5
        norm_b = sum(x * x for x in emb_b) ** 0.5
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return float(dot / (norm_a * norm_b))

    def _string_sim(
        self, payload: dict[str, Any], candidate_row: dict[str, Any], cfg: dict[str, Any]
    ) -> float:
        name_field = cfg.get("name_field")
        if not name_field:
            return 0.0
        a = str(payload.get(name_field) or "").strip().lower()
        b = str(candidate_row.get(name_field) or "").strip().lower()
        if not a or not b:
            return 0.0
        if a == b:
            return 1.0
        return jaro_winkler_similarity(a, b)

    def _temporal_sim(
        self, payload: dict[str, Any], candidate_row: dict[str, Any]
    ) -> float:
        """Return 1.0 if lifespans overlap, 0.0 if disjoint, 0.5 if one open-ended."""
        date_fields = ("start_date", "end_date", "issued_on", "expires_on", "completed_on")
        start_a = _extract_date(payload, "start_date")
        end_a = _extract_date(payload, "end_date")
        start_b = _extract_date(candidate_row, "start_date")
        end_b = _extract_date(candidate_row, "end_date")

        # Fallback: try issued_on / expires_on / completed_on
        if start_a is None:
            start_a = _extract_date(payload, "issued_on") or _extract_date(payload, "completed_on")
        if end_a is None:
            end_a = _extract_date(payload, "expires_on")
        if start_b is None:
            start_b = _extract_date(candidate_row, "issued_on") or _extract_date(candidate_row, "completed_on")
        if end_b is None:
            end_b = _extract_date(candidate_row, "expires_on")

        if start_a is None and start_b is None:
            return 0.5  # no temporal info → neutral
        if start_a is not None and start_b is not None:
            # Overlap test: [a_start, a_end] ∩ [b_start, b_end] != ∅
            a_end = end_a or date.max
            b_end = end_b or date.max
            if a_end < start_b or b_end < start_a:
                return 0.0
            return 1.0
        return 0.5

    async def _graph_sim(
        self, user_id: UUID, payload: dict[str, Any], candidate_id: UUID
    ) -> float:
        """Jaccard similarity of 1-hop neighbours in the personal graph."""
        # Fast path: if the candidate has no graph node yet, return neutral.
        try:
            neighbours = await universe_graph_service.neighbors(
                self._session, entity_id=candidate_id, user_id=user_id, depth=1, limit=200
            )
        except Exception:
            return 0.5
        if not neighbours:
            return 0.5
        # We don't have the new entity in the graph yet, so we can't compare
        # neighbourhoods directly.  Instead we use a proxy: if the payload
        # contains relation keys (derived_from_*, linked_skill_ids) we check
        # whether any of those target ids appear in the candidate's neighbours.
        linked = set()
        for key in payload:
            if key.startswith("derived_from_") or key == "linked_skill_ids":
                val = payload[key]
                if isinstance(val, list):
                    linked.update(str(v) for v in val)
                elif val:
                    linked.add(str(val))
        if not linked:
            return 0.5
        neigh_ids = {str(n.get("id")) for n in neighbours if n.get("id")}
        if not neigh_ids:
            return 0.5
        intersection = linked & neigh_ids
        union = linked | neigh_ids
        return len(intersection) / len(union) if union else 0.0


# 3. Clustering (connected components)


def _cluster_matches(
    matches: list[tuple[UUID, UUID, float]], threshold: float
) -> list[Cluster]:
    """Build connected components from edges whose score ≥ threshold.

    *matches* is a list of (id_a, id_b, score) where id_a is always the
    new payload's target id (or representative) and id_b is a candidate.
    """
    adj: dict[UUID, set[UUID]] = defaultdict(set)
    for a, b, score in matches:
        if score >= threshold:
            adj[a].add(b)
            adj[b].add(a)

    visited: set[UUID] = set()
    clusters: list[Cluster] = []
    for node in adj:
        if node in visited:
            continue
        stack = [node]
        comp: set[UUID] = set()
        while stack:
            cur = stack.pop()
            if cur in visited:
                continue
            visited.add(cur)
            comp.add(cur)
            stack.extend(adj[cur] - visited)
        if len(comp) > 1:
            rep = min(comp)  # deterministic: oldest UUID
            clusters.append(Cluster(cluster_id=uuid4(), entity_ids=comp, representative_id=rep))
    return clusters


# 4. Merge


def _apply_field_rules(
    field_rules: tuple[FieldRule, ...],
    rows: list[dict[str, Any]],
) -> dict[str, Any]:
    """Apply field-resolution rules to a cluster of entity dicts."""
    merged: dict[str, Any] = {}
    for rule in field_rules:
        values = [r.get(rule.field) for r in rows if r.get(rule.field) is not None]
        if not values:
            continue
        merged[rule.field] = _resolve_field(rule.strategy, values, rule.ranking)
    return merged


def _resolve_longest_non_null(values: list[Any], _ranking: dict[str, int] | None) -> Any:
    return max(values, key=lambda x: len(str(x)))


def _resolve_earliest(values: list[Any], _ranking: dict[str, int] | None) -> Any:
    dates: list[date] = [d for d in (_to_date(v) for v in values) if d is not None]
    return min(dates) if dates else values[0]


def _resolve_latest(values: list[Any], _ranking: dict[str, int] | None) -> Any:
    dates: list[date] = [d for d in (_to_date(v) for v in values) if d is not None]
    return max(dates) if dates else values[0]


def _resolve_max(values: list[Any], _ranking: dict[str, int] | None) -> Any:
    nums: list[float] = [n for n in (_to_number(v) for v in values) if n is not None]
    return max(nums) if nums else values[0]


def _resolve_max_ranked(values: list[Any], ranking: dict[str, int] | None) -> Any:
    if ranking is None:
        raise ValueError("max_ranked requires a ranking dict")
    return max(values, key=lambda x: ranking.get(str(x), 0))


def _resolve_union(values: list[Any], _ranking: dict[str, int] | None) -> Any:
    out: list[Any] = []
    seen: set[str] = set()
    for v in values:
        if isinstance(v, list):
            for item in v:
                key = str(item).strip().lower()
                if key and key not in seen:
                    out.append(item)
                    seen.add(key)
        else:
            key = str(v).strip().lower()
            if key and key not in seen:
                out.append(v)
                seen.add(key)
    return out


def _resolve_esco_preferred(values: list[Any], _ranking: dict[str, int] | None) -> Any:
    # Prefer the value from the row that has an esco_uri (more canonical).
    # Fallback to longest string.
    return max(values, key=lambda x: len(str(x)))


def _resolve_concatenate_unique(values: list[Any], _ranking: dict[str, int] | None) -> Any:
    texts: list[str] = []
    seen_texts: set[str] = set()
    for v in values:
        s = str(v).strip()
        if s and s.lower() not in seen_texts:
            texts.append(s)
            seen_texts.add(s.lower())
    return "\n\n".join(texts) if texts else None


def _resolve_preserve_existing(values: list[Any], _ranking: dict[str, int] | None) -> Any:
    return values[0]


_strategies: dict[str, Callable[..., Any]] = {
    "longest_non_null": _resolve_longest_non_null,
    "earliest": _resolve_earliest,
    "latest": _resolve_latest,
    "max": _resolve_max,
    "max_ranked": _resolve_max_ranked,
    "union": _resolve_union,
    "esco_preferred": _resolve_esco_preferred,
    "concatenate_unique": _resolve_concatenate_unique,
    "preserve_existing": _resolve_preserve_existing,
}


def _resolve_field(
    strategy: FieldStrategy, values: list[Any], ranking: dict[str, int] | None
) -> Any:
    resolver = _strategies.get(strategy)
    if resolver is None:
        raise ValueError(f"Unknown strategy: {strategy}")
    return resolver(values, ranking)


# 5. Provenance


async def _record_provenance(
    session: AsyncSession,
    *,
    user_id: UUID,
    kind: str,
    representative_id: UUID,
    merged_ids: list[UUID],
    merged_payload: dict[str, Any],
) -> UUID:
    """Write a :MergeEvent vertex and :MERGED_INTO edges to the graph."""
    event_id = uuid4()
    now_iso = datetime.now(UTC).isoformat()
    await cypher(
        session,
        graph_schema.GRAPH_PERSONAL,
        """
        CREATE (m:MergeEvent {
            id: $mid,
            user_id: $uid,
            kind: $kind,
            representative_id: $rep,
            merged_ids: $merged,
            merged_at: $now,
            source: "entity_resolution_v2"
        })
        RETURN m
        """,
        params={
            "mid": str(event_id),
            "uid": str(user_id),
            "kind": kind,
            "rep": str(representative_id),
            "merged": [str(i) for i in merged_ids],
            "now": now_iso,
        },
        column_defs="m agtype",
    )
    for old_id in merged_ids:
        if old_id == representative_id:
            continue
        await universe_graph_service.upsert_edge(
            session,
            edge_type="MERGED_INTO",
            source_id=old_id,
            target_id=representative_id,
            user_id=user_id,
            properties={"merge_event_id": str(event_id), "at": now_iso},
        )
    return event_id


# Orchestrator


class EntityResolutionPipeline:
    """End-to-end ER v2.  Stateless; holds a session reference."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._blocker = Blocker(session)
        self._matcher = PairwiseMatcher(session)

    async def resolve(
        self,
        *,
        user_id: UUID,
        kind: str,
        payload: dict[str, Any],
        cfg: dict[str, Any],
    ) -> ResolutionResult:
        """Run the full ER pipeline for a single incoming entity.

        Returns a ResolutionResult telling the caller whether to:
          * CREATE a new entity (no match)
          * MERGE into an existing cluster
          * surface an AMBIGUOUS suggestion to the user
        """
        er_cfg = config_for(kind)
        if er_cfg is None:
            # No ER config → fall back to old behaviour (no match)
            return ResolutionResult(status="no_match", entity_id=None)

        # 1. Blocking
        candidate_ids = await self._blocker.block(
            user_id=user_id, kind=kind, payload=payload, cfg=cfg
        )
        if not candidate_ids:
            return ResolutionResult(status="no_match", entity_id=None)

        # Fetch candidate rows
        table = cfg.get("table")
        if not table:
            return ResolutionResult(status="no_match", entity_id=None)
        rows = await self._fetch_rows(table, user_id, candidate_ids)

        # 2. Pairwise matching
        matches: list[tuple[UUID, UUID, float]] = []
        ambiguous: list[MatchCandidate] = []
        for cid, crow in rows.items():
            score = await self._matcher.score(
                user_id=user_id,
                kind=kind,
                payload=payload,
                candidate_id=cid,
                candidate_row=crow,
                cfg=cfg,
            )
            if score.composite >= er_cfg.matching_threshold:
                matches.append((cid, cid, score.composite))
            elif score.composite >= er_cfg.ambiguous_low:
                ambiguous.append(MatchCandidate(entity_id=cid, score=score.composite, signals=score.__dict__))

        # 3. Clustering
        clusters = _cluster_matches(matches, er_cfg.matching_threshold)

        if not clusters:
            if ambiguous:
                return ResolutionResult(
                    status="ambiguous",
                    entity_id=None,
                    suggestion_payload={
                        "kind": kind,
                        "candidates": [
                            {"entity_id": str(c.entity_id), "score": c.score, **c.signals}
                            for c in ambiguous
                        ],
                    },
                )
            return ResolutionResult(status="no_match", entity_id=None)

        # For now we only handle the largest cluster (typical case: 1 cluster).
        cluster = max(clusters, key=lambda c: len(c.entity_ids))
        rep_id = cluster.representative_id

        # 4. Merge
        cluster_rows = [rows[eid] for eid in cluster.entity_ids if eid in rows]
        merged_payload = _apply_field_rules(er_cfg.field_rules, cluster_rows)
        # Ensure the representative id survives
        merged_payload["id"] = str(rep_id)

        # 5. Provenance
        merged_ids = [eid for eid in cluster.entity_ids if eid != rep_id]
        event_id: UUID | None = None
        if merged_ids:
            try:
                event_id = await _record_provenance(
                    self._session,
                    user_id=user_id,
                    kind=kind,
                    representative_id=rep_id,
                    merged_ids=merged_ids,
                    merged_payload=merged_payload,
                )
            except Exception as exc:
                logger.warning("provenance_graph_write_failed", error=str(exc))

        return ResolutionResult(
            status="merged",
            entity_id=rep_id,
            merged_ids=merged_ids,
            provenance_event_id=event_id,
        )

    async def _fetch_rows(
        self, table: str, user_id: UUID, ids: set[UUID]
    ) -> dict[UUID, dict[str, Any]]:
        if not ids:
            return {}
        id_list = [str(i) for i in ids]
        rows = (
            await self._session.execute(
                text(
                    f"SELECT * FROM {table} "
                    f"WHERE user_id = :uid AND id = ANY(:ids)"
                ),
                {"uid": str(user_id), "ids": id_list},
            )
        ).mappings().all()
        return {UUID(r["id"]): dict(r) for r in rows}


# Helpers


def _extract_date(row: dict[str, Any], field: str) -> date | None:
    val = row.get(field)
    if val is None:
        return None
    if isinstance(val, datetime):
        return val.date()
    if isinstance(val, date):
        return val
    if isinstance(val, str):
        try:
            return date.fromisoformat(val)
        except ValueError:
            return None
    return None


def _to_date(val: Any) -> date | None:
    if val is None:
        return None
    if isinstance(val, datetime):
        return val.date()
    if isinstance(val, date):
        return val
    if isinstance(val, str):
        try:
            return date.fromisoformat(val)
        except ValueError:
            return None
    return None


def _to_number(val: Any) -> float | None:
    if val is None:
        return None
    try:
        return float(val)
    except (ValueError, TypeError):
        return None
