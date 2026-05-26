"""Reranking stage — the precision step after BM25+dense+PPR+RRF.

RRF is a strong *candidate generator* but it's rank-only and lane-agnostic: it
can't tell that, for the query "retrieval evaluation", `nDCG` beats `FastAPI`
even if both surfaced. A reranker scores each candidate *against the query*
directly. The literature is consistent: retrieve a wide pool cheaply, then
cross-encoder rerank the top-N for a large precision lift
(see https://www.elastic.co/docs/solutions/search/ranking/semantic-reranking).

Three implementations, chosen by config:
  • ``LLMListwiseReranker`` (default) — reuses the existing Anthropic/OpenAI
    client (`get_llm_client`) to order candidates. No new dependency or key.
    Falls back to identity order when the LLM is the mock provider.
  • ``HostedReranker`` — a hosted cross-encoder (Cohere / Voyage) when
    ``RERANK_API_KEY`` is set. Highest quality.
  • ``NoopReranker`` — identity; preserves the pure-RRF order.

Every implementation degrades to identity on error, so retrieval never breaks
because of the rerank stage.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

import structlog
from pydantic import BaseModel

from src.shared.config import get_settings
from src.shared.llm_client import get_llm_client

logger = structlog.get_logger(__name__)


@dataclass(slots=True)
class RerankCandidate:
    id: str
    text: str  # short surface form, e.g. "competencia · pgvector"


class Reranker(Protocol):
    name: str

    async def rerank(
        self, query: str, candidates: list[RerankCandidate], *, top_n: int
    ) -> list[tuple[str, float]]:
        """Return ordered ``[(id, score)]`` (most relevant first), len ≤ top_n."""
        ...


def _identity(candidates: list[RerankCandidate], top_n: int) -> list[tuple[str, float]]:
    n = len(candidates)
    return [(c.id, 1.0 - i / max(1, n)) for i, c in enumerate(candidates[:top_n])]


# --------------------------------------------------------------------------- #
# Noop
# --------------------------------------------------------------------------- #


class NoopReranker:
    name = "noop"

    async def rerank(
        self, query: str, candidates: list[RerankCandidate], *, top_n: int
    ) -> list[tuple[str, float]]:
        return _identity(candidates, top_n)


# --------------------------------------------------------------------------- #
# LLM listwise (default — no extra dependency)
# --------------------------------------------------------------------------- #


class _RankOrder(BaseModel):
    # Candidate indices, most relevant first. The LLM may omit clearly
    # irrelevant ones; we append any missing afterwards to preserve recall.
    order: list[int]


class LLMListwiseReranker:
    name = "llm"

    def __init__(self) -> None:
        self._llm = get_llm_client()

    async def rerank(
        self, query: str, candidates: list[RerankCandidate], *, top_n: int
    ) -> list[tuple[str, float]]:
        if not candidates:
            return []
        listing = "\n".join(f"[{i}] {c.text}" for i, c in enumerate(candidates))
        system = (
            "You rank a user's professional-graph entities by relevance to a "
            "query. Return ONLY a JSON object {\"order\": [indices]} listing the "
            "candidate indices from MOST to LEAST relevant. Judge semantic "
            "relevance to the query intent, not string overlap."
        )
        prompt = f"Query: {query}\n\nCandidates:\n{listing}"
        try:
            result = await self._llm.structured(
                system=system, prompt=prompt, schema=_RankOrder, max_tokens=512,
                temperature=0.0,
            )
        except Exception as exc:
            logger.warning("llm_rerank_failed", error=str(exc))
            return _identity(candidates, top_n)

        order = [i for i in (result.order or []) if 0 <= i < len(candidates)]
        if not order:
            # Mock client (or empty) → keep RRF order.
            return _identity(candidates, top_n)
        seen = set(order)
        order += [i for i in range(len(candidates)) if i not in seen]  # recall guard
        n = len(order)
        return [(candidates[i].id, 1.0 - rank / n) for rank, i in enumerate(order[:top_n])]


# --------------------------------------------------------------------------- #
# Hosted cross-encoder (Cohere / Voyage)
# --------------------------------------------------------------------------- #


class HostedReranker:
    name = "hosted"

    def __init__(self, provider: str, api_key: str, model: str | None) -> None:
        self._provider = provider
        self._api_key = api_key
        self._model = model or (
            "rerank-v3.5" if provider == "cohere" else "rerank-2"
        )

    async def rerank(
        self, query: str, candidates: list[RerankCandidate], *, top_n: int
    ) -> list[tuple[str, float]]:
        if not candidates:
            return []
        import httpx  # lazy

        url = (
            "https://api.cohere.com/v2/rerank"
            if self._provider == "cohere"
            else "https://api.voyageai.com/v1/rerank"
        )
        payload = {
            "model": self._model,
            "query": query,
            "documents": [c.text for c in candidates],
            "top_n": min(top_n, len(candidates)),
        }
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(
                    url,
                    headers={"Authorization": f"Bearer {self._api_key}"},
                    json=payload,
                )
                resp.raise_for_status()
                data = resp.json()
        except Exception as exc:
            logger.warning("hosted_rerank_failed", provider=self._provider, error=str(exc))
            return _identity(candidates, top_n)

        out: list[tuple[str, float]] = []
        for r in data.get("results", []):
            idx = r.get("index")
            score = float(r.get("relevance_score", 0.0))
            if isinstance(idx, int) and 0 <= idx < len(candidates):
                out.append((candidates[idx].id, score))
        return out or _identity(candidates, top_n)


# --------------------------------------------------------------------------- #
# Factory
# --------------------------------------------------------------------------- #


_reranker: Reranker | None = None


def get_reranker() -> Reranker:
    global _reranker
    if _reranker is not None:
        return _reranker
    s = get_settings()
    if not s.rerank_enabled or s.rerank_provider == "none":
        _reranker = NoopReranker()
    elif s.rerank_provider in {"cohere", "voyage"} and s.rerank_api_key:
        _reranker = HostedReranker(s.rerank_provider, s.rerank_api_key, s.rerank_model)
    else:
        # "llm" (default) or hosted-without-key → LLM listwise (identity if mock).
        _reranker = LLMListwiseReranker()
    return _reranker


def reset_reranker() -> None:
    """Test-only."""
    global _reranker
    _reranker = None
