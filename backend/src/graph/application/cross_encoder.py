"""Lightweight cross-encoder reranker for ESCO candidate resolution.

This module provides a feature-based reranker that re-scores ESCO candidates
using local string-similarity signals. It requires no GPU and no heavy
dependencies — a stop-gap until a full neural cross-encoder is justified.

Signals used:
  • Jaro-Winkler similarity on normalized strings (phonetic/typo robust)
  • Token Jaccard overlap (word-level coverage)
  • Exact prefix/suffix match bonus
  • Original retrieval rank decay (top candidates get a small boost)

The reranker is deterministic, fast, and interpretable.
"""
from __future__ import annotations

from dataclasses import dataclass

import structlog

from src.graph.domain.esco_types import EscoCandidate

logger = structlog.get_logger(__name__)


def _tokenize(text: str) -> set[str]:
    """Simple whitespace tokenization with normalization."""
    return set(text.lower().split())


def _jaccard(a: set[str], b: set[str]) -> float:
    """Jaccard similarity between two token sets."""
    if not a or not b:
        return 0.0
    inter = len(a & b)
    union = len(a | b)
    return inter / union if union else 0.0


def _jaro_winkler(a: str, b: str) -> float:
    """Jaro-Winkler similarity using jellyfish."""
    try:
        from jellyfish import jaro_winkler_similarity

        return float(jaro_winkler_similarity(a, b))
    except Exception:
        return 0.0


def _exact_substring_bonus(query: str, candidate_label: str) -> float:
    """Bonus when query is an exact substring of candidate or vice versa."""
    q = query.lower()
    c = candidate_label.lower()
    if q == c:
        return 1.0
    if q in c or c in q:
        return 0.5
    return 0.0


@dataclass(frozen=True)
class RerankScore:
    candidate: EscoCandidate
    original_score: float
    rerank_score: float
    features: dict[str, float]


class FeatureReranker:
    """Re-rank ESCO candidates using lightweight local features.

    Weights (tuned for ESCO skill/occupation labels):
      jaro_winkler  0.35
      jaccard       0.25
      exact_bonus   0.20
      rank_decay    0.20  (1.0 for rank 0, 0.85 for rank 1, …)
    """

    _WEIGHTS: dict[str, float] = {
        "jaro_winkler": 0.35,
        "jaccard": 0.25,
        "exact_bonus": 0.20,
        "rank_decay": 0.20,
    }

    def rerank(
        self,
        query: str,
        candidates: list[EscoCandidate],
        *,
        weights: dict[str, float] | None = None,
    ) -> list[RerankScore]:
        """Return candidates sorted by reranked score (descending)."""
        w = weights or self._WEIGHTS
        query_norm = query.lower().strip()
        query_tokens = _tokenize(query_norm)

        scored: list[RerankScore] = []
        for rank, cand in enumerate(candidates):
            label = (cand.pref_label_es or cand.pref_label_en or "").lower().strip()
            if not label:
                label = cand.uri.split("/")[-1].replace("-", " ").lower()

            jw = _jaro_winkler(query_norm, label)
            jac = _jaccard(query_tokens, _tokenize(label))
            exact = _exact_substring_bonus(query_norm, label)
            rank_decay = max(0.5, 1.0 - rank * 0.05)

            features = {
                "jaro_winkler": jw,
                "jaccard": jac,
                "exact_bonus": exact,
                "rank_decay": rank_decay,
            }

            rerank_score = sum(features[k] * w.get(k, 0.0) for k in features)
            scored.append(
                RerankScore(
                    candidate=cand,
                    original_score=cand.score,
                    rerank_score=rerank_score,
                    features=features,
                )
            )

        scored.sort(key=lambda x: x.rerank_score, reverse=True)
        return scored

    def best(
        self,
        query: str,
        candidates: list[EscoCandidate],
        *,
        threshold: float = 0.75,
    ) -> EscoCandidate | None:
        """Return the top reranked candidate if it passes threshold."""
        if not candidates:
            return None
        ranked = self.rerank(query, candidates)
        top = ranked[0]
        if top.rerank_score >= threshold:
            logger.info(
                "esco_rerank_matched",
                query=query,
                uri=top.candidate.uri,
                rerank_score=round(top.rerank_score, 3),
                original_score=round(top.original_score, 3),
                features=top.features,
            )
            # Mutate the candidate score in-place so downstream code sees the reranked value
            top.candidate.score = top.rerank_score
            return top.candidate
        logger.info(
            "esco_rerank_below_threshold",
            query=query,
            top_score=round(top.rerank_score, 3),
            threshold=threshold,
        )
        return None


# Module-level singleton — stateless, safe to share.
feature_reranker = FeatureReranker()
