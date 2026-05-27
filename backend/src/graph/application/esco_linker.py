"""ESCO entity linker — bridges personal entities to the shared ontology.

Pipeline:

  1. Normalise the input text (NFKC, lowercase, abbreviation expansion).
  2. Candidate generation: pgvector top-K cosine against
     `ontology_embeddings` filtered by `label`.
  3. Cross-encoder rerank: FeatureReranker re-scores candidates using
     Jaro-Winkler + token Jaccard + exact-match bonus + rank decay.
  4. Resolution:

       rerank_score ≥ THRESHOLD_AUTO       → LINKED      (returns esco_uri)
       rerank_score ≥ THRESHOLD_QUARANTINE → SUGGESTED   (returns top-3)
       else                                → ORPHAN      (fallback to custom ontology)

The thresholds apply to the *reranked* score, not the raw cosine. This
reduces false positives from polysemous terms (e.g. "Java" the island
vs "Java" the language) because the string-similarity signals penalise
label mismatches even when embeddings are close.
"""
from __future__ import annotations

import unicodedata
from typing import Literal

import structlog
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.graph.application.cross_encoder import feature_reranker
from src.graph.domain import custom_skills_ontology as cso
from src.graph.domain.esco_types import EscoCandidate, EscoLinkResult, LinkState
from src.shared.embeddings import get_embeddings_service
from src.shared.metrics import discovery_esco_links_total

logger = structlog.get_logger(__name__)


# Tuning constants — see the v2 plan for rationale.

THRESHOLD_AUTO: float = 0.86
"""Cosine score above which we auto-link. Picked from internal smoke
tests; "AWS Lambda" matches "amazon lambda function" at ~0.87."""

THRESHOLD_QUARANTINE: float = 0.70
"""Below auto, above this we send to the user for confirmation."""

CANDIDATE_TOP_K: int = 5
"""How many candidates we ask the user to choose between in the SUGGESTED
state. Three works in mobile chat; five gives ESCO's broader/narrower
options some room when the surface labels are very generic."""


# Normalisation

_ABBREV_EXPANSIONS = {
    "aws": "amazon web services",
    "gcp": "google cloud platform",
    "azure": "microsoft azure",
    "k8s": "kubernetes",
    "k8": "kubernetes",
    "ml": "machine learning",
    "ai": "artificial intelligence",
    "llm": "large language model",
    "ci": "continuous integration",
    "cd": "continuous delivery",
    "ci/cd": "continuous integration continuous delivery",
    "iac": "infrastructure as code",
    "sql": "structured query language",
    "nosql": "non relational database",
    "api": "application programming interface",
    "ux": "user experience",
    "ui": "user interface",
    "qa": "quality assurance",
    "dba": "database administration",
}


def normalise(text_in: str) -> str:
    """Stable normalisation pipeline used by both candidate gen and rerank.

    Idempotent and side-effect-free, so callers can cache the output.
    """
    if not text_in:
        return ""
    normal = unicodedata.normalize("NFKC", text_in).strip().lower()
    # Expand standalone abbreviations (token boundary, not substring).
    tokens = []
    for tok in normal.split():
        clean = tok.strip(".,;:()[]")
        expanded = _ABBREV_EXPANSIONS.get(clean)
        tokens.append(expanded if expanded else tok)
    return " ".join(tokens)


# Result types


class EscoEntityLinker:
    """Stateless service — call `link()` per term."""

    async def link(
        self,
        session: AsyncSession,
        text_in: str,
        kind: Literal["skill", "occupation"],
        *,
        threshold_auto: float = THRESHOLD_AUTO,
        threshold_quarantine: float = THRESHOLD_QUARANTINE,
        top_k: int = CANDIDATE_TOP_K,
    ) -> EscoLinkResult:
        normalised = normalise(text_in)
        if not normalised:
            result = EscoLinkResult(state=LinkState.ORPHAN, reason="empty input")
            discovery_esco_links_total.labels(state=result.state.value).inc()
            return result

        # 1. Embed the query.
        provider = get_embeddings_service()
        try:
            query_vec = await provider.embed(normalised)
        except Exception as exc:
            logger.warning("esco_linker_embed_failed", error=str(exc))
            result = EscoLinkResult(state=LinkState.ERROR, reason="embed_failed")
            discovery_esco_links_total.labels(state=result.state.value).inc()
            return result

        # 2. Candidate generation via pgvector + label hydration in ONE
        #    query. asyncpg only accepts the vector as a "[v1,v2,...]"
        #    string literal. We LEFT JOIN ontology_search (migration 0015)
        #    so prefLabels come back inline — no per-candidate Cypher.
        target_label = "EscoSkill" if kind == "skill" else "Occupation"
        vec_literal = "[" + ",".join(f"{x:.7f}" for x in query_vec) + "]"
        rows = (
            await session.execute(
                text(
                    """
                    SELECT
                        oe.uri AS uri,
                        oe.label AS label,
                        os.pref_label_es AS pref_label_es,
                        os.pref_label_en AS pref_label_en,
                        1 - (oe.embedding <=> CAST(:q AS vector)) AS score
                    FROM ontology_embeddings oe
                    LEFT JOIN ontology_search os ON os.uri = oe.uri
                    WHERE oe.label = :target
                      AND oe.embedding IS NOT NULL
                    ORDER BY oe.embedding <=> CAST(:q AS vector)
                    LIMIT :top_k
                    """
                ),
                {"q": vec_literal, "target": target_label, "top_k": top_k},
            )
        ).all()
        if not rows:
            result = EscoLinkResult(
                state=LinkState.ORPHAN, reason="no candidates in ontology"
            )
            discovery_esco_links_total.labels(state=result.state.value).inc()
            return result

        candidates = [
            EscoCandidate(
                uri=row.uri,
                label=row.label,
                pref_label_es=row.pref_label_es,
                pref_label_en=row.pref_label_en,
                score=float(row.score),
            )
            for row in rows
        ]

        # 3b. Cross-encoder rerank.
        reranked = feature_reranker.rerank(normalised, candidates)
        if not reranked:
            result = EscoLinkResult(
                state=LinkState.ORPHAN, reason="rerank returned empty"
            )
            discovery_esco_links_total.labels(state=result.state.value).inc()
            return result

        # 4. Resolution on reranked scores.
        top = reranked[0]
        result: EscoLinkResult
        if top.rerank_score >= threshold_auto:
            result = EscoLinkResult(
                state=LinkState.LINKED,
                esco_uri=top.candidate.uri,
                candidates=[top.candidate],
                score=top.rerank_score,
                reason="linked via embedding + rerank",
            )
        elif top.rerank_score >= threshold_quarantine:
            result = EscoLinkResult(
                state=LinkState.SUGGESTED,
                candidates=[r.candidate for r in reranked[:CANDIDATE_TOP_K]],
                score=top.rerank_score,
                reason="below auto-link threshold after rerank",
            )
        else:
            # 5. Fallback to custom AI-era ontology when ESCO has no match.
            custom = cso.find_by_label(normalised)
            if custom is None:
                custom_hits = cso.search_by_text(normalised)
                custom = custom_hits[0] if custom_hits else None
            if custom is not None:
                result = EscoLinkResult(
                    state=LinkState.LINKED,
                    esco_uri=custom.uri,
                    candidates=[
                        EscoCandidate(
                            uri=custom.uri,
                            label="CustomSkill",
                            pref_label_es=custom.pref_label_es,
                            pref_label_en=custom.pref_label_en,
                            score=0.95,
                        )
                    ],
                    score=0.95,
                    reason="linked via custom skills ontology",
                )
            else:
                result = EscoLinkResult(
                    state=LinkState.ORPHAN,
                    candidates=[r.candidate for r in reranked[:CANDIDATE_TOP_K]],
                    score=top.rerank_score,
                    reason="top candidate below quarantine threshold after rerank",
                )
        discovery_esco_links_total.labels(state=result.state.value).inc()
        return result


# Module-level singleton — stateless, safe to share.
esco_linker = EscoEntityLinker()
