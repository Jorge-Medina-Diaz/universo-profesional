"""Unit tests for ESCO linker custom-skills fallback.

When ESCO returns ORPHAN (top candidate below quarantine), the linker
must fall back to the in-memory custom AI-era ontology.
"""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from src.graph.application.esco_linker import EscoEntityLinker, LinkState


class _FakeDbRow:
    def __init__(
        self,
        uri: str,
        label: str,
        pref_label_es: str | None,
        pref_label_en: str | None,
        score: float,
    ) -> None:
        self.uri = uri
        self.label = label
        self.pref_label_es = pref_label_es
        self.pref_label_en = pref_label_en
        self.score = score


@pytest.mark.asyncio
async def test_custom_skill_linking_for_mcp() -> None:
    linker = EscoEntityLinker()
    with patch(
        "src.graph.application.esco_linker.get_embeddings_service"
    ) as mock_embed:
        mock_embed.return_value = AsyncMock()
        mock_embed.return_value.embed = AsyncMock(return_value=[0.1] * 1536)

        mock_session = AsyncMock()
        mock_result = MagicMock()
        # Return a fake low-scoring DB row so the linker does not early-exit.
        mock_result.all.return_value = [
            _FakeDbRow("esco:fake", "EscoSkill", None, None, 0.1)
        ]
        mock_session.execute.return_value = mock_result

        with patch(
            "src.graph.application.esco_linker.normalise",
            return_value="model context protocol",
        ), patch(
            "src.graph.application.esco_linker.feature_reranker.rerank"
        ) as mock_rerank:
            # Force rerank score below quarantine so custom ontology is tried.
            mock_rerank.return_value = [
                MagicMock(candidate=MagicMock(uri="esco:fake"), rerank_score=0.5)
            ]
            result = await linker.link(
                mock_session,
                "MCP",
                "skill",
            )

    assert result.state == LinkState.LINKED
    assert result.esco_uri == "up:ai/mcp"
    assert result.score == 0.95


@pytest.mark.asyncio
async def test_custom_skill_linking_for_rag() -> None:
    linker = EscoEntityLinker()
    with patch(
        "src.graph.application.esco_linker.get_embeddings_service"
    ) as mock_embed:
        mock_embed.return_value = AsyncMock()
        mock_embed.return_value.embed = AsyncMock(return_value=[0.1] * 1536)

        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.all.return_value = [
            _FakeDbRow("esco:fake", "EscoSkill", None, None, 0.1)
        ]
        mock_session.execute.return_value = mock_result

        with patch(
            "src.graph.application.esco_linker.normalise",
            return_value="rag pipeline",
        ), patch(
            "src.graph.application.esco_linker.feature_reranker.rerank"
        ) as mock_rerank:
            mock_rerank.return_value = [
                MagicMock(candidate=MagicMock(uri="esco:fake"), rerank_score=0.5)
            ]
            result = await linker.link(
                mock_session,
                "RAG pipeline",
                "skill",
            )

    assert result.state == LinkState.LINKED
    assert result.esco_uri == "up:ai/rag-pipeline"


@pytest.mark.asyncio
async def test_no_fallback_for_common_skill() -> None:
    """A skill that IS in ESCO should not hit the custom ontology."""
    linker = EscoEntityLinker()
    with patch(
        "src.graph.application.esco_linker.get_embeddings_service"
    ) as mock_embed:
        mock_embed.return_value = AsyncMock()
        mock_embed.return_value.embed = AsyncMock(return_value=[0.1] * 1536)

        # Simulate a normalised term that the custom ontology does NOT know.
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.all.return_value = [
            _FakeDbRow("esco:fake", "EscoSkill", None, None, 0.1)
        ]
        mock_session.execute.return_value = mock_result

        with patch(
            "src.graph.application.esco_linker.normalise",
            return_value="plumber",
        ), patch(
            "src.graph.application.esco_linker.feature_reranker.rerank"
        ) as mock_rerank:
            mock_rerank.return_value = [
                MagicMock(candidate=MagicMock(uri="esco:fake"), rerank_score=0.5)
            ]
            result = await linker.link(
                mock_session,
                "plumber",
                "skill",
            )

    # Custom ontology does not know "plumber" → ORPHAN.
    assert result.state == LinkState.ORPHAN
