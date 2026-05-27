"""Unit tests for the CommunityRetriever (4th lane).

Verifies that the retriever issues the correct pgvector SQL and returns
ScoredItem objects with deterministic pseudo-entity IDs.
"""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from src.graph.application.retrieval import CommunityRetriever


class _FakeRow:
    def __init__(self, community_id: str, label: str, summary: str, score: float) -> None:
        self.id = community_id
        self.label = label
        self.summary = summary
        self.score = score


@pytest.mark.asyncio
async def test_community_retriever_issues_vector_query() -> None:
    user_id = uuid4()
    retriever = CommunityRetriever()

    mock_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.all.return_value = [
        _FakeRow("comm-1", "Cloud Architecture", "AWS and infra work", 0.88)
    ]
    mock_session.execute.return_value = mock_result

    with patch(
        "src.graph.application.retrieval.communities.get_embeddings_service"
    ) as mock_embed:
        mock_embed.return_value = AsyncMock()
        mock_embed.return_value.embed = AsyncMock(return_value=[0.1] * 1536)

        items = await retriever.retrieve(mock_session, user_id, "cloud skills")

    assert len(items) == 1
    assert items[0].kind == "community"
    assert items[0].name == "Cloud Architecture"
    assert items[0].score == 0.88
    assert items[0].rationale == "AWS and infra work"
    # Deterministic pseudo-ID so RRF treats it uniformly.
    assert items[0].entity_id is not None

    # Verify the SQL contained the distance operator.
    calls = mock_session.execute.call_args_list
    sql_text = str(calls[0][0][0])
    assert "<=>" in sql_text


@pytest.mark.asyncio
async def test_community_retriever_empty_on_embed_failure() -> None:
    user_id = uuid4()
    retriever = CommunityRetriever()

    mock_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.all.return_value = []
    mock_session.execute.return_value = mock_result

    with patch(
        "src.graph.application.retrieval.communities.get_embeddings_service"
    ) as mock_embed:
        mock_embed.return_value = AsyncMock()
        mock_embed.return_value.embed = AsyncMock(side_effect=RuntimeError("down"))

        items = await retriever.retrieve(mock_session, user_id, "anything")

    assert items == []
