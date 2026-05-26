"""Unit tests for ESCO linker custom-skills fallback.

When ESCO returns ORPHAN (top candidate below quarantine), the linker
must fall back to the in-memory custom AI-era ontology.
"""
from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from src.graph.application.esco_linker import EscoEntityLinker, LinkState


@pytest.mark.asyncio
async def test_custom_skill_linking_for_mcp() -> None:
    linker = EscoEntityLinker()
    with patch(
        "src.graph.application.esco_linker.get_embeddings_service"
    ) as mock_embed:
        mock_embed.return_value = AsyncMock()
        mock_embed.return_value.embed = AsyncMock(return_value=[0.1] * 1536)

        with patch(
            "src.graph.application.esco_linker.normalise",
            return_value="model context protocol",
        ):
            result = await linker.link(
                None,  # type: ignore[arg-type]
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

        with patch(
            "src.graph.application.esco_linker.normalise",
            return_value="rag pipeline",
        ):
            result = await linker.link(
                None,  # type: ignore[arg-type]
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
        with patch(
            "src.graph.application.esco_linker.normalise",
            return_value="plumber",
        ):
            # Since we don't have a real DB, the ESCO candidate gen will
            # return empty → ORPHAN. The custom ontology also won't know
            # "plumber" → final ORPHAN.
            result = await linker.link(
                None,  # type: ignore[arg-type]
                "plumber",
                "skill",
            )

    # No mock DB rows => ORPHAN because plumber is not in custom ontology.
    assert result.state == LinkState.ORPHAN
