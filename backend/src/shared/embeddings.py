"""Embeddings service.

Two providers wired:

  * `DeterministicEmbeddingsProvider` — SHA-256-derived pseudo embeddings.
    Free, stable across runs, but NOT semantically meaningful. Use for
    dev/CI/tests.
  * `OpenAIEmbeddingsProvider` — text-embedding-3-small via direct httpx
    (no SDK). 1536-dim, ~$0.02/1M tokens. Real semantic search.

`get_embeddings_provider()` returns the OpenAI one if
`EMBEDDINGS_PROVIDER=openai` AND `OPENAI_API_KEY` is set; otherwise it
falls back to deterministic with a warning. This means dev environments
without an OpenAI key still work end-to-end (just with garbage similarity
scores).
"""
from __future__ import annotations

import asyncio
import hashlib
import math
from typing import Protocol

import httpx
import structlog
from tenacity import (
    AsyncRetrying,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from .config import get_settings

logger = structlog.get_logger(__name__)

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


class OpenAIEmbeddingsProvider:
    """text-embedding-3-small via direct httpx — no openai SDK dependency.

    Single requests use `/embeddings`; batch ups uses the same endpoint with
    a list `input` (OpenAI accepts up to 2048 items per call, but we keep
    batches small for retry-friendliness).
    """

    dim: int = EMBEDDING_DIM
    BATCH_SIZE = 64

    def __init__(
        self,
        api_key: str,
        *,
        model: str = "text-embedding-3-small",
        base_url: str = "https://api.openai.com/v1",
        timeout: float = 30.0,
    ) -> None:
        self._model = model
        self._client = httpx.AsyncClient(
            base_url=base_url,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            timeout=httpx.Timeout(timeout, connect=5.0),
        )

    async def embed(self, text: str) -> list[float]:
        out = await self._post([text or "<empty>"])
        return out[0]

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        results: list[list[float]] = []
        # Chunk by BATCH_SIZE to keep retries cheap and avoid hitting per-request limits.
        for i in range(0, len(texts), self.BATCH_SIZE):
            batch = [t or "<empty>" for t in texts[i : i + self.BATCH_SIZE]]
            results.extend(await self._post(batch))
        return results

    async def _post(self, inputs: list[str]) -> list[list[float]]:
        async for attempt in AsyncRetrying(
            stop=stop_after_attempt(3),
            wait=wait_exponential(multiplier=2, min=2, max=10),
            retry=retry_if_exception_type(
                (httpx.HTTPStatusError, httpx.RequestError, asyncio.TimeoutError)
            ),
            reraise=True,
        ):
            with attempt:
                resp = await self._client.post(
                    "/embeddings",
                    json={
                        "model": self._model,
                        "input": inputs,
                        "dimensions": EMBEDDING_DIM,
                    },
                )
                resp.raise_for_status()
                payload = resp.json()
                return [item["embedding"] for item in payload["data"]]
        # Unreachable — tenacity with reraise=True raises on failure.
        raise RuntimeError("OpenAI embeddings failed without an exception")

    async def aclose(self) -> None:
        await self._client.aclose()


_provider: EmbeddingsProvider | None = None


def get_embeddings_provider() -> EmbeddingsProvider:
    """Return the active embeddings provider, honoring settings + fallback.

    Resolution order:
      1. `EMBEDDINGS_PROVIDER=openai` + `OPENAI_API_KEY` → OpenAI (real).
      2. `EMBEDDINGS_PROVIDER=deterministic` or anything else → Deterministic.
      3. If `openai` was requested but key missing → warn + Deterministic.
    """
    global _provider
    if _provider is not None:
        return _provider
    settings = get_settings()
    # Resolved: a bare OPENAI_API_KEY auto-upgrades from the deterministic
    # default to real OpenAI embeddings (see Settings.embeddings_provider_resolved).
    chosen = (settings.embeddings_provider_resolved or "deterministic").strip().lower()
    if chosen == "openai":
        key = (settings.openai_api_key or "").strip() if hasattr(settings, "openai_api_key") else ""
        if not key:
            logger.warning(
                "embeddings_provider_fallback",
                requested=chosen,
                reason="OPENAI_API_KEY not set",
                using="deterministic",
            )
            _provider = DeterministicEmbeddingsProvider()
        else:
            _provider = OpenAIEmbeddingsProvider(api_key=key)
            logger.info("embeddings_provider_ready", provider="openai")
    else:
        _provider = DeterministicEmbeddingsProvider()
    return _provider


# Backwards-compatibility alias — keep older code paths working.
get_embeddings_service = get_embeddings_provider


def reset_embeddings_provider() -> None:
    """Test-only: reset cached provider."""
    global _provider
    _provider = None


reset_embeddings_service = reset_embeddings_provider
