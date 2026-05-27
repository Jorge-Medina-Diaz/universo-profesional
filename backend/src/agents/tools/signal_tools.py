"""Signal tools — agent access to the rubric overlay (per-user, per-chunk).

These tools expose `user_rubric_signals` to specialists so they can talk
about concrete criteria/signals, not generic areas:

  - `get_user_rubric_coverage(rubric_slug?, sector?, status?)` — list signals
    + which entities sustain them. The bread-and-butter of tech_radar and
    portfolio specialists.
  - `recompute_user_signals(sector?)` — cold path; force refresh after bulk
    imports.
"""
from __future__ import annotations
from src.agents.tools._deps import require_user_id

from typing import Any
from uuid import UUID

from agno.run.base import RunContext
from agno.tools import tool

from src.shared.db import with_user_session
from src.universe.application.signal_extraction import (
    extract_user_signals,
    list_user_signals_with_chunk,
)


@require_user_id
@tool(
    name="get_user_rubric_coverage",
    description=(
        "Return the user's coverage of the rubric corpus — which specific "
        "criteria/signals/anti-patterns they own/practice/aspire-to, with "
        "evidence references. Filter by `sector` (backend|frontend|cloud|"
        "data_eng|...) and/or `status` (own|practice|aspire|teach|avoid). "
        "Use this BEFORE narrating gaps — it gives signal-level granularity "
        "that `get_universe_shape` (area-level) can't."
    ),
)
async def get_user_rubric_coverage(
    run_context: RunContext,
    sector: str | None = None,
    status: str | None = None,
    top_k: int = 20,
) -> dict[str, Any]:
    user_id = run_context.user_id
    user_uuid = UUID(user_id)
    async with with_user_session(user_uuid) as session:
        rows = await list_user_signals_with_chunk(
            session, user_uuid, sector=sector, status=status
        )
    # Trim chunk bodies for the agent (saves context tokens).
    trimmed: list[dict[str, Any]] = []
    for r in rows[:top_k]:
        body = (r.get("body_md") or "")
        if len(body) > 280:
            body = body[:280].rsplit(" ", 1)[0] + "…"
        trimmed.append(
            {
                "signal_id": str(r["signal_id"]),
                "rubric_chunk_id": str(r["rubric_chunk_id"]),
                "rubric_slug": r.get("rubric_slug"),
                "rubric_title": r.get("rubric_title"),
                "sector": r.get("sector"),
                "section_kind": r.get("section_kind"),
                "heading": r.get("heading"),
                "body_excerpt": body,
                "status": r.get("status"),
                "confidence": float(r.get("confidence", 0)),
                "evidence_entity_type": r.get("evidence_entity_type"),
                "evidence_count": len(r.get("evidence_entity_ids") or []),
            }
        )
    by_status: dict[str, int] = {}
    for r in rows:
        s = r.get("status") or "unknown"
        by_status[s] = by_status.get(s, 0) + 1
    return {
        "ok": True,
        "total": len(rows),
        "filtered_sector": sector,
        "filtered_status": status,
        "by_status": by_status,
        "signals": trimmed,
    }


@require_user_id
@tool(
    name="recompute_user_signals",
    description=(
        "Force a recompute of the user's rubric overlay (which chunks they "
        "own/practice/aspire). Use after bulk imports (LinkedIn / PDF CV) "
        "or when the user explicitly asks to refresh. Optional `sector` "
        "filter limits the scope (cheaper)."
    ),
)
async def recompute_user_signals(
    run_context: RunContext,
    sector: str | None = None,
) -> dict[str, Any]:
    user_id = run_context.user_id
    user_uuid = UUID(user_id)
    async with with_user_session(user_uuid) as session:
        result = await extract_user_signals(session, user_uuid, sector=sector)
    return {
        "ok": True,
        "sector": sector,
        "signals_created": result.signals_created,
        "signals_updated": result.signals_updated,
        "signals_removed": result.signals_removed,
        "by_status": result.by_status,
    }
