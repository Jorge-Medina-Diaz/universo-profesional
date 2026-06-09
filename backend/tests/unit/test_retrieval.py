"""Smoke tests for the hybrid retriever's pure pieces (no DB).

Covers Reciprocal Rank Fusion — the algorithm that fuses the BM25 /
dense / PPR / community lanes. The DB-backed lanes are exercised manually
+ by the integration suite; RRF is pure and the most important to lock down.
"""
from __future__ import annotations

import asyncio
from uuid import uuid4

from src.graph.application.retrieval import (
    ScoredItem,
    reciprocal_rank_fusion,
)
from src.graph.application.retrieval._base import HybridResult
from src.graph.application.retrieval.fusion import _ppr_seeds, _rerank


def _ranking(lane: str, ids: list) -> list[ScoredItem]:
    return [
        ScoredItem(
            entity_id=eid,
            kind="skill",
            name=f"n{i}",
            score=1.0 - i * 0.1,
            rank=i + 1,
            lane=lane,
        )
        for i, eid in enumerate(ids)
    ]


def test_rrf_rewards_items_ranked_by_multiple_lanes() -> None:
    a, b, c = uuid4(), uuid4(), uuid4()
    # `a` appears top in two lanes; `b` only in one; `c` only in one.
    bm25 = _ranking("bm25", [a, b])
    dense = _ranking("dense", [a, c])
    fused = reciprocal_rank_fusion([bm25, dense], k=60, top_k=10)
    # `a` (in both lanes) must rank first.
    assert fused[0].entity_id == a
    assert fused[0].fused_score > fused[1].fused_score


def test_rrf_four_lanes_boosts_cross_lane_candidates() -> None:
    a, b, c, d = uuid4(), uuid4(), uuid4(), uuid4()
    bm25 = _ranking("bm25", [a, b])
    dense = _ranking("dense", [a, c])
    ppr = _ranking("ppr", [a, d])
    community = _ranking("community", [b])
    fused = reciprocal_rank_fusion([bm25, dense, ppr, community], k=60, top_k=10)
    # `a` in 3 lanes should outrank everyone.
    assert fused[0].entity_id == a


def test_rrf_respects_top_k() -> None:
    ids = [uuid4() for _ in range(20)]
    fused = reciprocal_rank_fusion([_ranking("bm25", ids)], k=60, top_k=5)
    assert len(fused) == 5


def test_rrf_handles_empty_lanes() -> None:
    a = uuid4()
    fused = reciprocal_rank_fusion([[], _ranking("dense", [a])], k=60, top_k=10)
    assert len(fused) == 1
    assert fused[0].entity_id == a


def test_rrf_records_lane_contributions() -> None:
    a = uuid4()
    fused = reciprocal_rank_fusion(
        [_ranking("bm25", [a]), _ranking("dense", [a]), _ranking("community", [a])],
        k=60,
        top_k=10,
    )
    assert set(fused[0].contributions.keys()) == {"bm25", "dense", "community"}


def test_rrf_k_constant_is_standard() -> None:
    # The canonical RRF k is 60 — verify the math matches 1/(k+rank).
    a = uuid4()
    fused = reciprocal_rank_fusion([_ranking("bm25", [a])], k=60, top_k=1)
    assert abs(fused[0].fused_score - (1.0 / 61)) < 1e-9


# ---------------------------------------------------------------------------
# PPR seed selection — dense ∪ BM25 (structural lane stays lit on keyword hits)
# ---------------------------------------------------------------------------


def _scored(lane: str, eid, score: float, rank: int) -> ScoredItem:
    return ScoredItem(
        entity_id=eid, kind="skill", name="n", score=score, rank=rank, lane=lane
    )


def test_ppr_seeds_includes_bm25_when_dense_is_weak() -> None:
    a, b = uuid4(), uuid4()
    # dense surfaces `a` but BELOW the 0.5 cosine gate; bm25 nails `b` (exact
    # name). Without the union, PPR would get NO seed → structural lane dark.
    dense = [_scored("dense", a, 0.40, 1)]
    bm25 = [_scored("bm25", b, 9.9, 1)]
    seeds = _ppr_seeds(dense, bm25)
    assert b in seeds  # bm25 hit becomes a seed
    assert a not in seeds  # below the dense 0.5 gate


def test_ppr_seeds_dedup_and_dense_first() -> None:
    a, b = uuid4(), uuid4()
    dense = [_scored("dense", a, 0.9, 1)]
    bm25 = [_scored("bm25", a, 9.9, 1), _scored("bm25", b, 8.0, 2)]
    seeds = _ppr_seeds(dense, bm25)
    assert seeds == [a, b]  # `a` once (dedup), dense-first ordering preserved


def test_ppr_seeds_caps_each_lane_to_three() -> None:
    dense = [_scored("dense", uuid4(), 0.9, i + 1) for i in range(5)]
    bm25 = [_scored("bm25", uuid4(), 9.0, i + 1) for i in range(5)]
    seeds = _ppr_seeds(dense, bm25)
    assert len(seeds) == 6  # top-3 dense + top-3 bm25 (disjoint ids)


# ---------------------------------------------------------------------------
# Rerank latency gate — skip the LLM round-trip when the pool isn't wider
# ---------------------------------------------------------------------------


def _hres(eid, score: float) -> HybridResult:
    return HybridResult(entity_id=eid, kind="skill", name="n", fused_score=score)


def test_rerank_gate_skips_when_pool_not_wider_than_top_k(monkeypatch) -> None:
    import src.graph.application.reranker as rr

    def _boom():  # pragma: no cover - must never be called
        raise AssertionError("reranker must not run when len(fused) <= top_k")

    monkeypatch.setattr(rr, "get_reranker", _boom)
    fused = [_hres(uuid4(), 0.5), _hres(uuid4(), 0.4), _hres(uuid4(), 0.3)]
    out = asyncio.run(_rerank("q", fused, top_k=12))
    assert [r.entity_id for r in out] == [r.entity_id for r in fused]  # RRF order kept


def test_rerank_runs_when_pool_wider_than_top_k(monkeypatch) -> None:
    import src.graph.application.reranker as rr

    class _RevReranker:
        name = "rev"

        async def rerank(self, query, candidates, *, top_n):
            rev = list(reversed(candidates))[:top_n]
            return [(c.id, 1.0 - i / max(1, len(rev))) for i, c in enumerate(rev)]

    monkeypatch.setattr(rr, "get_reranker", lambda: _RevReranker())
    ids = [uuid4() for _ in range(6)]
    fused = [_hres(e, 1.0 - i * 0.1) for i, e in enumerate(ids)]
    out = asyncio.run(_rerank("q", fused, top_k=3))
    assert len(out) == 3  # gate inactive (6 > 3) → reranker ran, filtered to top_k
    assert out[0].entity_id == ids[-1]  # reversed order → last fused first


# ---------------------------------------------------------------------------
# Redis snapshot helpers (pure / no DB)
# ---------------------------------------------------------------------------


def test_redis_key_format() -> None:
    from src.graph.application.retrieval import _redis_key

    uid = uuid4()
    assert _redis_key(uid) == f"ppr:snapshot:{uid}"


def test_pickle_snapshot_roundtrip() -> None:
    """Verify _UserSnapshot is picklable (required for Redis store/load)."""
    import pickle
    from uuid import uuid4

    import igraph as ig
    from src.graph.application.retrieval import _UserSnapshot

    g = ig.Graph(directed=True)
    g.add_vertices(2)
    g.add_edge(0, 1)
    snap = _UserSnapshot(
        graph=g,
        id_to_idx={uuid4(): 0, uuid4(): 1},
        idx_to_meta={0: (uuid4(), "skill", "Python"), 1: (uuid4(), "skill", "R")},
        idx_to_esco={0: None, 1: "http://data.europa.eu/esco/skill/123"},
        built_at=1234.0,
    )
    payload = pickle.dumps(snap)
    restored = pickle.loads(payload)
    assert restored.graph.vcount() == 2
    assert restored.graph.ecount() == 1
