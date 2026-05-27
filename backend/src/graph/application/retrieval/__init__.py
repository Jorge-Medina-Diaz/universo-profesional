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

from src.graph.application.retrieval._base import HybridResult, Retriever, ScoredItem
from src.graph.application.retrieval._helpers import (
    _attach_ranks,
    _coerce_uuid,
    _strip_quotes,
    _table_has_column,
)
from src.graph.application.retrieval.bm25 import BM25Retriever
from src.graph.application.retrieval.communities import CommunityRetriever
from src.graph.application.retrieval.dense import DenseRetriever
from src.graph.application.retrieval.fusion import (
    _rerank,
    hybrid_retrieve,
    reciprocal_rank_fusion,
)
from src.graph.application.retrieval.ppr import PPRRetriever
from src.graph.application.retrieval.snapshot import (
    _load_snapshot,
    _redis_key,
    _UserSnapshot,
    invalidate_snapshot,
)

__all__ = [
    "BM25Retriever",
    "CommunityRetriever",
    "DenseRetriever",
    "HybridResult",
    "PPRRetriever",
    "Retriever",
    "ScoredItem",
    "_UserSnapshot",
    "_attach_ranks",
    "_coerce_uuid",
    "_load_snapshot",
    "_redis_key",
    "_rerank",
    "_strip_quotes",
    "_table_has_column",
    "hybrid_retrieve",
    "invalidate_snapshot",
    "reciprocal_rank_fusion",
]
