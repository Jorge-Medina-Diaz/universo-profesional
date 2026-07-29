"""Unit tests for embeddings provider."""
from __future__ import annotations

import math

import pytest
from src.shared.embeddings import (
    DeterministicEmbeddingsProvider,
    get_embeddings_provider,
    reset_embeddings_provider,
)


class TestDeterministicEmbeddingsProvider:
    def test_embed_sync_non_empty(self):
        provider = DeterministicEmbeddingsProvider()
        vec = provider._embed_sync("hello")
        assert len(vec) == provider.dim
        assert all(-1 <= x <= 1 for x in vec)

    def test_embed_sync_empty_text(self):
        provider = DeterministicEmbeddingsProvider()
        vec = provider._embed_sync("")
        assert len(vec) == provider.dim

    def test_embed_sync_deterministic(self):
        provider = DeterministicEmbeddingsProvider()
        v1 = provider._embed_sync("test")
        v2 = provider._embed_sync("test")
        assert v1 == v2

    def test_embed_sync_normalized(self):
        provider = DeterministicEmbeddingsProvider()
        vec = provider._embed_sync("hello")
        norm = math.sqrt(sum(x * x for x in vec))
        assert norm == pytest.approx(1.0, 0.01)

    def test_embed_sync_different_texts(self):
        provider = DeterministicEmbeddingsProvider()
        v1 = provider._embed_sync("hello")
        v2 = provider._embed_sync("world")
        assert v1 != v2


class TestGetEmbeddingsProvider:
    def test_returns_provider(self):
        reset_embeddings_provider()
        provider = get_embeddings_provider()
        assert provider is not None

