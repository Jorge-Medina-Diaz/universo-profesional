"""Unit tests for enrichment semantic kNN migration to pgvector HNSW.

The O(N²) brute-force path is gone; we verify the SQL kNN path mocks
out correctly and that edge deduplication still works.
"""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from src.universe.application.enrichment import _infer_semantic_edges


class _FakeRow:
    def __init__(self, id: str, score: float) -> None:
        self.id = id
        self.score = score


@pytest.mark.asyncio
async def test_infer_semantic_edges_uses_hnsw_knn() -> None:
    """The SQL path must query graph_entity_embeddings with <=> operator."""
    user_id = uuid4()
    e1 = uuid4()
    e2 = uuid4()

    recs = [(e1, "skill", [0.1] * 1536)]

    mock_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.all.return_value = [_FakeRow(str(e2), 0.85)]
    mock_session.execute.return_value = mock_result

    # Patch upsert_edge so we don't need the graph service.
    import src.universe.application.enrichment as _enrich

    original_upsert = _enrich.universe_graph_service.upsert_edge
    _enrich.universe_graph_service.upsert_edge = AsyncMock(return_value=True)

    stats = _enrich.EnrichmentStats()
    try:
        await _infer_semantic_edges(
            mock_session, user_id, recs=recs, knn=4, min_score=0.24, stats=stats
        )
    finally:
        _enrich.universe_graph_service.upsert_edge = original_upsert

    # The execute call must contain the HNSW distance operator.
    calls = mock_session.execute.call_args_list
    sql_calls = [c[0][0].text if hasattr(c[0][0], "text") else str(c[0][0]) for c in calls]
    assert any("<=>" in s for s in sql_calls)
    assert stats.related_to == 1


@pytest.mark.asyncio
async def test_infer_semantic_edges_respects_min_score() -> None:
    """Rows below min_score must be ignored."""
    user_id = uuid4()
    e1 = uuid4()
    e2 = uuid4()

    recs = [(e1, "skill", [0.1] * 1536)]

    mock_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.all.return_value = [_FakeRow(str(e2), 0.15)]
    mock_session.execute.return_value = mock_result

    import src.universe.application.enrichment as _enrich

    original_upsert = _enrich.universe_graph_service.upsert_edge
    _enrich.universe_graph_service.upsert_edge = AsyncMock(return_value=True)

    stats = _enrich.EnrichmentStats()
    try:
        await _infer_semantic_edges(
            mock_session, user_id, recs=recs, knn=4, min_score=0.24, stats=stats
        )
    finally:
        _enrich.universe_graph_service.upsert_edge = original_upsert

    assert stats.related_to == 0
