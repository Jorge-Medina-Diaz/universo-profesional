"""Embeddings service.

For the MVP we use a **deterministic** embedding derived from SHA-256 of the
text. This:
  * preserves dimension (1536 floats, matching OpenAI text-embedding-3-small)
  * produces unit-norm vectors so cosine similarity behaves correctly
  * is stable across runs and free
  * is similar-text-aware enough for tests: identical text → identical vector,
    different text → different vector. It is *not* semantically meaningful,
    so production must switch via `EMBEDDINGS_PROVIDER=openai|mistral`.

Real providers can be added by implementing the `EmbeddingsProvider` Protocol
and wiring in `get_embeddings_service()`.
"""
from __future__ import annotations

import hashlib
import math
from typing import Protocol

from .config import get_settings

EMBEDDING_DIM = 1536


class EmbeddingsProvider(Protocol):
    async def embed(self, text: str) -> list[float]: ...
    async def embed_batch(self, texts: list[str]) -> list[list[float]]: ...


class DeterministicEmbeddingsProvider:
    """SHA-256-derived pseudo-embeddings. Deterministic, free, dimension-stable."""

    dim: int = EMBEDDING_DIM

    async def embed(self, text: str) -> list[float]:
        return self._embed_sync(text)

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        return [self._embed_sync(t) for t in texts]

    @staticmethod
    def _embed_sync(text: str) -> list[float]:
        if not text:
            text = "<empty>"
        normalized = text.strip().lower()
        # Produce enough bytes by chaining SHA-256 with a counter.
        bytes_needed = EMBEDDING_DIM * 4  # 4 bytes per float32 component
        chunks = bytearray()
        counter = 0
        seed = normalized.encode("utf-8")
        while len(chunks) < bytes_needed:
            digest = hashlib.sha256(seed + counter.to_bytes(4, "big")).digest()
            chunks.extend(digest)
            counter += 1
        chunks = chunks[:bytes_needed]
        # Convert to floats in [-1, 1]
        floats = []
        for i in range(0, bytes_needed, 4):
            word = int.from_bytes(chunks[i : i + 4], "big", signed=False)
            # Map uint32 → [-1, 1]
            floats.append((word / 0xFFFFFFFF) * 2 - 1)
        # L2-normalize so cosine == dot product
        norm = math.sqrt(sum(x * x for x in floats)) or 1.0
        return [x / norm for x in floats]


_provider: EmbeddingsProvider | None = None


def get_embeddings_service() -> EmbeddingsProvider:
    global _provider
    if _provider is not None:
        return _provider
    settings = get_settings()
    if settings.embeddings_provider == "deterministic":
        _provider = DeterministicEmbeddingsProvider()
    else:
        # Real providers wired here in v1.
        raise NotImplementedError(
            f"Embeddings provider {settings.embeddings_provider!r} not implemented yet. "
            "Set EMBEDDINGS_PROVIDER=deterministic for MVP."
        )
    return _provider


def reset_embeddings_service() -> None:
    """Test-only: reset cached provider."""
    global _provider
    _provider = None
