"""Agent tools for the rubrics corpus.

  - `search_rubrics(query, sector?, section_kind?, top_k=5)` — semantic search
     against `rubric_chunks` with optional filters. Returns the top-k chunks
     (heading + body_md + score) so the agent can ground its questions and
     suggestions in expert criteria.
  - `list_rubric_sectors()` — coverage report (sector + doc_count) so the
     coordinator knows what's available before deciding to query.

Both are read-only and safe to call multiple times per turn (cheap, cached
embeddings on small queries).
"""
from __future__ import annotations

from typing import Any

from agno.run.base import RunContext
from agno.tools import tool

from src.rubrics.infrastructure.repository import RubricRepository
from src.shared.db import with_user_session
from src.shared.embeddings import get_embeddings_provider

# Trim retrieved bodies so we don't blow up the context window.
MAX_BODY_CHARS = 800


@tool(
    name="search_rubrics",
    description=(
        "Search the system's curated rubrics corpus — sector-specific criteria, "
        "guiding questions, seniority signals, anti-patterns and resources. "
        "Use BEFORE asking deep questions or making suggestions so they're "
        "grounded in real expertise, not generic advice.\n\n"
        "Filters:\n"
        "  - `sector`: one of 'backend', 'frontend', 'devops', 'mobile', "
        "'ai_ml', 'data_eng', 'security', 'design_systems', 'general'.\n"
        "  - `section_kind`: 'criteria' | 'questions' | 'signals' | "
        "'anti_patterns' | 'resources' | 'general'. Use 'questions' when you "
        "want guiding questions to ask the user; 'signals' for seniority "
        "markers; 'criteria' for what good looks like.\n"
        "Returns up to `top_k` chunks with {slug, sector, heading, "
        "section_kind, body_md, score}. Scores are cosine similarity (1.0 = "
        "perfect match). If all scores < 0.55, treat as no match and fall "
        "back to your own knowledge."
    ),
)
async def search_rubrics(
    run_context: RunContext,
    query: str,
    sector: str | None = None,
    section_kind: str | None = None,
    top_k: int = 5,
) -> dict[str, Any]:
    query = (query or "").strip()
    if not query:
        return {"ok": False, "error": "empty query"}
    if top_k <= 0 or top_k > 20:
        top_k = 5
    embedder = get_embeddings_provider()
    try:
        query_emb = await embedder.embed(query)
    except Exception as e:
        return {"ok": False, "error": f"embedding failed: {e}"}
    async with with_user_session(None) as session:
        repo = RubricRepository(session)
        try:
            rows = await repo.search_chunks(
                query_embedding=query_emb,
                sector=sector,
                section_kind=section_kind,
                top_k=top_k,
            )
        except Exception as e:
            return {"ok": False, "error": f"search failed: {e}"}
    results = []
    for r in rows:
        body = r.get("body_md") or ""
        if len(body) > MAX_BODY_CHARS:
            body = body[:MAX_BODY_CHARS].rstrip() + "…"
        results.append(
            {
                "slug": r.get("slug"),
                "sector": r.get("sector"),
                "section_kind": r.get("section_kind"),
                "heading": r.get("heading"),
                "body_md": body,
                "tags": list(r.get("tags") or []),
                "score": round(float(r.get("score") or 0.0), 3),
            }
        )
    return {"ok": True, "count": len(results), "results": results}


@tool(
    name="list_rubric_sectors",
    description=(
        "Return the list of sectors covered by the rubrics corpus and the "
        "number of documents per sector. Useful to know whether a topic has "
        "rubric coverage before relying on `search_rubrics`."
    ),
)
async def list_rubric_sectors(run_context: RunContext) -> dict[str, Any]:
    async with with_user_session(None) as session:
        repo = RubricRepository(session)
        sectors = await repo.list_sectors()
    return {"ok": True, "sectors": sectors, "total_sectors": len(sectors)}
