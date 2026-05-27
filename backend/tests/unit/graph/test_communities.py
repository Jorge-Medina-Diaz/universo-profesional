"""Unit tests for CommunityRetriever exception path (no DB)."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

from src.graph.application.retrieval.communities import CommunityRetriever


class TestCommunityRetriever:
    async def test_embed_failure_returns_empty(self):
        retriever = CommunityRetriever()
        with patch.object(retriever._embedder, "embed", side_effect=RuntimeError("fail")):
            result = await retriever.retrieve(MagicMock(), MagicMock(), "query")
            assert result == []
