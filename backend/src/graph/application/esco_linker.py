"""ESCO entity linker — bridges personal entities to the shared ontology.

Pipeline (matches the design in §N.1 of the v2 plan):

  1. Normalise the input text (NFKC, lowercase, abbreviation expansion).
  2. Candidate generation: pgvector top-K cosine against the
     `ontology_embeddings` table, filtered by `label` so a skill is only
     compared to :EscoSkill and an occupation only to :Occupation.
  3. Cross-encoder rerank — *deferred* to a future sprint when we ship a
     small open-source reranker. Until then the score is cosine alone.
  4. Resolution:

       score ≥ THRESHOLD_AUTO       → LINKED      (returns esco_uri)
       score ≥ THRESHOLD_QUARANTINE → SUGGESTED   (returns top-3)
       else                         → ORPHAN      (no link, no quarantine)

The thresholds are deliberately conservative. False positives are far
worse than false negatives because once a personal entity carries an
`esco_uri`, all downstream retrieval (PPR seeds, signal extraction)
treats it as authoritative. A SUGGESTED row goes into `entity_quarantine`
and the coordinator surfaces it to the user via the HITL flow added in
N.5.
"""
from __future__ import annotations

import unicodedata
from dataclasses import dataclass, field
from enum import Enum
from typing import Literal

import structlog
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.shared.embeddings import get_embeddings_service

logger = structlog.get_logger(__name__)


# ---------------------------------------------------------------------------
# Tuning constants — see the v2 plan for rationale.
# ---------------------------------------------------------------------------

THRESHOLD_AUTO: float = 0.86
"""Cosine score above which we auto-link. Picked from internal smoke
tests; "AWS Lambda" matches "amazon lambda function" at ~0.87."""

THRESHOLD_QUARANTINE: float = 0.70
"""Below auto, above this we send to the user for confirmation."""

CANDIDATE_TOP_K: int = 5
"""How many candidates we ask the user to choose between in the SUGGESTED
state. Three works in mobile chat; five gives ESCO's broader/narrower
options some room when the surface labels are very generic."""


# ---------------------------------------------------------------------------
# Normalisation
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# Result types
# ---------------------------------------------------------------------------


class LinkState(str, Enum):
    LINKED = "linked"
    SUGGESTED = "suggested"
    ORPHAN = "orphan"
    ERROR = "error"


@dataclass(slots=True)
class EscoCandidate:
    uri: str
    label: str          # AGE vertex label: "EscoSkill" or "Occupation"
    pref_label_es: str | None
    pref_label_en: str | None
    score: float        # cosine in [0, 1]


@dataclass(slots=True)
class EscoLinkResult:
    state: LinkState
    esco_uri: str | None = None
    candidates: list[EscoCandidate] = field(default_factory=list)
    score: float | None = None  # top candidate score
    reason: str | None = None


# ---------------------------------------------------------------------------
# Linker
# ---------------------------------------------------------------------------


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
            return EscoLinkResult(state=LinkState.ORPHAN, reason="empty input")

        # 1. Embed the query.
        provider = get_embeddings_service()
        try:
            query_vec = await provider.embed(normalised)
        except Exception as exc:
            logger.warning("esco_linker_embed_failed", error=str(exc))
            return EscoLinkResult(state=LinkState.ERROR, reason="embed_failed")

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
            return EscoLinkResult(
                state=LinkState.ORPHAN, reason="no candidates in ontology"
            )

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

        # 4. Resolution.
        top = candidates[0]
        if top.score >= threshold_auto:
            return EscoLinkResult(
                state=LinkState.LINKED,
                esco_uri=top.uri,
                candidates=candidates[:1],
                score=top.score,
            )
        if top.score >= threshold_quarantine:
            return EscoLinkResult(
                state=LinkState.SUGGESTED,
                candidates=candidates,
                score=top.score,
                reason="below auto-link threshold",
            )
        return EscoLinkResult(
            state=LinkState.ORPHAN,
            candidates=candidates,
            score=top.score,
            reason="top candidate below quarantine threshold",
        )


# Module-level singleton — stateless, safe to share.
esco_linker = EscoEntityLinker()
