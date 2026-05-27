from __future__ import annotations

from collections.abc import Iterable
from uuid import UUID

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from src.graph.application.retrieval._base import HybridResult, ScoredItem
from src.graph.application.retrieval.bm25 import BM25Retriever
from src.graph.application.retrieval.communities import CommunityRetriever
from src.graph.application.retrieval.dense import DenseRetriever
from src.graph.application.retrieval.ppr import PPRRetriever

logger = structlog.get_logger(__name__)


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
