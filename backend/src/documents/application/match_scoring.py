"""Pure match-scoring helpers shared by the jobs `/score` REST endpoint and the
`match_job_to_profile` MCP tool, so the Kanban scorecard and the agent's
`present_job_match` widget always agree.

Given the entities retrieved from the user's universe (semantic search) plus the
JD's ATS keywords and the user's known skills, we derive an overall match score
and a grounded per-dimension breakdown (skills / experience / education).

We deliberately do NOT invent a "culture fit" score: nothing in the universe
data grounds it, and a fabricated number would mislead the user about how the
match was computed.
"""
from __future__ import annotations

from typing import Any

# Which retrieved entity_type contributes to which headline dimension.
_DIMENSION_OF: dict[str, str] = {
    "skill": "skills",
    "certification": "skills",
    "course": "skills",
    "language": "skills",
    "experience": "experience",
    "project": "experience",
    "achievement": "experience",
    "artifact": "experience",
    "architecture_decision": "experience",
    "interest": "experience",
    "education": "education",
}

DIMENSIONS = ("skills", "experience", "education")

# How many of the strongest matches per dimension we average. Averaging *all*
# retrieved rows would punish a deep universe (lots of weakly-related entities);
# the top-N reflects "do your best-matching N items cover this dimension".
_TOP_PER_DIM = 5


def _norm(cosine: float) -> float:
    """Map a cosine similarity in [-1, 1] to a [0, 1] confidence."""
    return max(0.0, min(1.0, (cosine + 1.0) / 2.0))


def compute_match_breakdown(
    *,
    retrieved: list[dict[str, Any]],
    needed_keywords: list[str],
    your_skills: list[str],
) -> dict[str, Any]:
    """Compute the headline score plus a per-dimension breakdown.

    ``retrieved`` items are the semantic-search rows: each carries ``entity_type``
    and a cosine ``score``. ``needed_keywords`` are the JD's ATS keywords;
    ``your_skills`` the names of the user's skill entities.
    """
    scores = [float(r.get("score", 0.0)) for r in retrieved]
    if scores:
        avg = sum(scores) / len(scores)
        # Keep the headline number identical to the legacy formula so cached
        # scores don't visibly shift when this richer breakdown ships.
        overall = int(round(max(0.0, min(1.0, (avg + 1.0) / 2.0)) * 100))
    else:
        # Nothing retrieved → no match. (The legacy formula mapped an empty
        # universe to a misleading 50% via cosine 0 → (0+1)/2.)
        overall = 0

    dimensions: dict[str, int | None] = {}
    for dim in DIMENSIONS:
        bucket = sorted(
            (
                _norm(float(r.get("score", 0.0)))
                for r in retrieved
                if _DIMENSION_OF.get(str(r.get("entity_type"))) == dim
            ),
            reverse=True,
        )
        if bucket:
            top = bucket[:_TOP_PER_DIM]
            dimensions[dim] = int(round((sum(top) / len(top)) * 100))
        else:
            dimensions[dim] = None

    needed = {k.lower().strip() for k in needed_keywords if k and k.strip()}
    have = {s.lower().strip() for s in your_skills if s and s.strip()}
    strengths = sorted(have & needed)
    gaps = sorted(needed - have)
    keyword_coverage = (
        int(round(100 * len(strengths) / len(needed))) if needed else None
    )

    return {
        "match_score": overall,
        "dimensions": dimensions,
        "strengths": strengths,
        "gaps": gaps,
        "keyword_coverage": keyword_coverage,
        "suggested_keywords": list(needed_keywords)[:15],
    }
