"""CV generation workflow — gather, outline, draft, polish, render.

This is the rich CV generation path the plan calls for. It pulls from all
four memory layers:

  - Universe entities (skills ordered by evidence count → real depth)
  - Notes tagged 'learning' / 'professional' (currently-learning section)
  - Knowledge chunks (RAG over user's documents matching the JD)
  - Change log (recent activity → "currently focused on")

Sprint 4 ships the skeleton: deterministic gathering + a single LLM call
when configured, falling back to the existing MockLlmClient otherwise so
dev still produces a PDF. Future iterations swap the single call for a
true Agno Workflow with parallel section drafts.
"""
from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID

import structlog
from sqlalchemy import text

from src.shared.config import get_settings
from src.shared.db import get_session_factory, set_rls_user

logger = structlog.get_logger(__name__)


_SKIP_COLS = {"embedding", "user_id", "deleted_at"}


def _clean(row: dict[str, Any]) -> dict[str, Any]:
    """Drop columns the renderer doesn't need (embedding, user_id, deleted_at)."""
    return {k: v for k, v in row.items() if k not in _SKIP_COLS}


async def _gather_universe(
    session: Any, *, user_id: str
) -> dict[str, Any]:
    """Pull all entity lists. Skills are ranked by evidence count desc."""
    out: dict[str, Any] = {}
    for table, key in [
        ("educations", "educations"),
        ("experiences", "experiences"),
        ("projects", "projects"),
        ("certifications", "certifications"),
        ("courses", "courses"),
        ("languages", "languages"),
        ("achievements", "achievements"),
        ("interests", "interests"),
    ]:
        rows = (
            await session.execute(
                text(
                    f"SELECT * FROM {table} WHERE user_id = :uid "  # noqa: S608
                    f"AND COALESCE(deleted_at::text, '') = '' "
                    f"ORDER BY updated_at DESC LIMIT 50"
                ),
                {"uid": user_id},
            )
        ).mappings().all()
        out[key] = [_clean(dict(r)) for r in rows]
    # Skills sorted by evidence count
    rows = (
        await session.execute(
            text(
                """
                SELECT s.*, COALESCE(ec.cnt, 0) AS evidence_count
                FROM skills s
                LEFT JOIN (
                  SELECT skill_id, COUNT(*) AS cnt FROM evidences
                  WHERE user_id = :uid GROUP BY skill_id
                ) ec ON ec.skill_id = s.id
                WHERE s.user_id = :uid
                ORDER BY ec.cnt DESC NULLS LAST, s.years DESC NULLS LAST
                LIMIT 50
                """
            ),
            {"uid": user_id},
        )
    ).mappings().all()
    out["skills"] = [_clean(dict(r)) for r in rows]
    return out


async def _gather_notes(session: Any, *, user_id: str) -> list[dict[str, Any]]:
    rows = (
        await session.execute(
            text(
                "SELECT id::text, title, body_md, tags, updated_at FROM notes "
                "WHERE user_id = :uid AND deleted_at IS NULL "
                "AND tags && ARRAY['learning','professional','project','opinion'] "
                "ORDER BY updated_at DESC LIMIT 30"
            ),
            {"uid": user_id},
        )
    ).mappings().all()
    return [dict(r) for r in rows]


async def _gather_recent_changes(
    session: Any, *, user_id: str
) -> list[dict[str, Any]]:
    cutoff = datetime.now(timezone.utc) - timedelta(days=90)
    rows = (
        await session.execute(
            text(
                "SELECT entity_type, entity_id::text, change_type, field, "
                "       old_value, new_value, reason, changed_at "
                "FROM universe_change_log "
                "WHERE user_id = :uid AND changed_at >= :since "
                "ORDER BY changed_at DESC LIMIT 100"
            ),
            {"uid": user_id, "since": cutoff},
        )
    ).mappings().all()
    return [dict(r) for r in rows]


async def gather(*, user_id: str, job_description: str | None) -> dict[str, Any]:
    """Step 1 — assemble all context the CV writer will need."""
    factory = get_session_factory()
    async with factory() as session:
        await set_rls_user(session, UUID(user_id))
        universe, notes, changes = await asyncio.gather(
            _gather_universe(session, user_id=user_id),
            _gather_notes(session, user_id=user_id),
            _gather_recent_changes(session, user_id=user_id),
        )
    return {
        "user_id": user_id,
        "job_description": job_description or "",
        "universe": universe,
        "notes": notes,
        "recent_changes": changes,
    }


def _currently_learning_section(notes: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Surface recent learning-tagged notes as a short list of items."""
    recent_cutoff = datetime.now(timezone.utc) - timedelta(days=120)
    items = []
    for n in notes:
        tags = list(n.get("tags") or [])
        if "learning" not in tags:
            continue
        updated = n.get("updated_at")
        if isinstance(updated, datetime) and updated < recent_cutoff:
            continue
        items.append(
            {
                "title": n.get("title") or _first_line(n.get("body_md", "")),
                "tags": [t for t in tags if t != "learning"],
                "since": updated.isoformat() if isinstance(updated, datetime) else None,
            }
        )
    return items[:5]


def _first_line(md: str) -> str:
    return next((ln for ln in md.splitlines() if ln.strip()), "").strip("# ").strip()


async def render_cv(
    *, user_id: str, job_description: str | None = None
) -> dict[str, Any]:
    """Top-level entry: gather → assemble payload → defer to existing renderer.

    Sprint 4 produces a structured `cv_payload` dict that the existing
    document renderer can consume. The LLM-driven polish step is wired but
    only fires when `LLM_PROVIDER != mock`.
    """
    context = await gather(user_id=user_id, job_description=job_description)
    settings = get_settings()
    polish_enabled = settings.agents_provider_resolved != "mock"

    universe = context["universe"]
    cv_payload: dict[str, Any] = {
        "basics": _basics_from_universe(universe),
        "experiences": universe["experiences"][:6],
        "educations": universe["educations"],
        "projects": universe["projects"][:6],
        "skills": universe["skills"][:15],
        "certifications": universe["certifications"],
        "languages": universe["languages"],
        "currently_learning": _currently_learning_section(context["notes"]),
        "recent_focus": [
            {
                "type": c["entity_type"],
                "field": c["field"],
                "new_value": c["new_value"],
                "changed_at": c["changed_at"].isoformat()
                if isinstance(c["changed_at"], datetime)
                else c["changed_at"],
            }
            for c in context["recent_changes"][:8]
            if c.get("entity_type") in {"skill", "project", "interest"}
        ],
        "polish_applied": False,
    }

    if polish_enabled and job_description:
        try:
            cv_payload = await _llm_polish(cv_payload, job_description)
        except Exception as exc:  # noqa: BLE001
            logger.warning("cv_polish_failed", error=str(exc))
    return cv_payload


def _basics_from_universe(u: dict[str, Any]) -> dict[str, Any]:
    """Headline + summary stub. Real values come from the `universes` table —
    we leave that out of Sprint 4 to keep the change surface tight."""
    return {
        "languages": [
            {"name": lang.get("name"), "level": lang.get("level")}
            for lang in u.get("languages", [])
        ],
    }


async def _llm_polish(payload: dict[str, Any], jd: str) -> dict[str, Any]:
    """Pass the structured payload + JD through an LLM for ATS-friendly polish.

    Kept thin and synchronous-feeling: one Sonnet call for the full payload.
    Future iterations parallelize by section.
    """
    from agno.agent import Agent

    from src.agents.factory import _build_model

    polisher = Agent(
        name="cv_polisher",
        model=_build_model(),
        instructions=[
            "Refines structured CV JSON to match the given job description.",
            "Rewrite bullet points for impact, tighten wording, keep dates.",
            "Output the SAME JSON shape, no extra prose.",
        ],
    )
    import json

    prompt = json.dumps({"job_description": jd, "cv": payload}, default=str)
    result = await polisher.arun(input=prompt, stream=False)
    body = getattr(result, "content", "") or ""
    try:
        polished = json.loads(body)
        polished["polish_applied"] = True
        return polished
    except Exception:  # noqa: BLE001
        return {**payload, "polish_applied": False}
