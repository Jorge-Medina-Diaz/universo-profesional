"""Smoke tests for the hybrid retriever's pure pieces (no DB).

Covers Reciprocal Rank Fusion — the algorithm that fuses the BM25 /
dense / PPR lanes. The DB-backed lanes are exercised manually + by the
integration suite; RRF is pure and the most important to lock down.
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
        [_ranking("bm25", [a]), _ranking("dense", [a])], k=60, top_k=10
    )
    assert set(fused[0].contributions.keys()) == {"bm25", "dense"}


def test_rrf_k_constant_is_standard() -> None:
    # The canonical RRF k is 60 — verify the math matches 1/(k+rank).
    a = uuid4()
    fused = reciprocal_rank_fusion([_ranking("bm25", [a])], k=60, top_k=1)
    assert abs(fused[0].fused_score - (1.0 / 61)) < 1e-9
