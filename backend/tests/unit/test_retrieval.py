"""Smoke tests for the hybrid retriever's pure pieces (no DB).

Covers Reciprocal Rank Fusion — the algorithm that fuses the BM25 /
dense / PPR / community lanes. The DB-backed lanes are exercised manually
+ by the integration suite; RRF is pure and the most important to lock down.
"""
from __future__ import annotations

from uuid import uuid4

from src.graph.application.retrieval import (
    ScoredItem,
    reciprocal_rank_fusion,
)


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
        built_at=1234.0,
    )
    payload = pickle.dumps(snap)
    restored = pickle.loads(payload)
    assert restored.graph.vcount() == 2
    assert restored.graph.ecount() == 1
