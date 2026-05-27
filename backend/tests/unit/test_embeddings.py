"""Unit tests for deterministic embeddings."""
from __future__ import annotations

import math

import pytest
from src.shared.embeddings import EMBEDDING_DIM, DeterministicEmbeddingsProvider


@pytest.mark.asyncio
async def test_dimension_is_1536() -> None:
    p = DeterministicEmbeddingsProvider()
    v = await p.embed("hello world")
    assert len(v) == EMBEDDING_DIM


@pytest.mark.asyncio
async def test_unit_norm() -> None:
    p = DeterministicEmbeddingsProvider()
    v = await p.embed("python developer")
    norm = math.sqrt(sum(x * x for x in v))
    assert abs(norm - 1.0) < 1e-6


@pytest.mark.asyncio
async def test_deterministic() -> None:
    p = DeterministicEmbeddingsProvider()
    a = await p.embed("Senior backend engineer")
    b = await p.embed("Senior backend engineer")
    assert a == b


@pytest.mark.asyncio
async def test_different_texts_different_vectors() -> None:
    p = DeterministicEmbeddingsProvider()
    a = await p.embed("Python")
    b = await p.embed("TypeScript")
    assert a != b


@pytest.mark.asyncio
async def test_empty_text_handled() -> None:
    p = DeterministicEmbeddingsProvider()
    v = await p.embed("")
    assert len(v) == EMBEDDING_DIM
