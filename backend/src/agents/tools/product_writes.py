"""Product writes — agent-side updates on jobs, preferences, reminders.

These are server-side (no HITL) and intended to run AFTER a `confirm_destructive`
or `propose_preferences_update` card has received the user's go-ahead. Use them
as the *commit step* of an HITL flow; do not call them speculatively.
"""
from __future__ import annotations
from src.agents.tools._deps import require_user_id

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from agno.run.base import RunContext
from agno.tools import tool

from src.shared.db import with_user_session

VALID_JOB_STATUSES = {
    "interested",
    "applied",
    "interviewing",
    "offer",
    "rejected",
    "archived",
}


@require_user_id
@tool(
    name="update_preferences",
    description=(
        "Patch the user's career preferences. `patch` is a dict with any of: "
        "status, salary_min, salary_max, salary_currency, contract_types[], "
        "remote_preference, open_to_relocate, working_areas[], "
        "perks_must_have[], perks_nice_to_have[], preferred_competences[], "
        "discarded_competences[], preferred_roles[], discarded_roles[], "
        "motivations. Merges into the existing record (does not replace it). "
        "Returns the new state."
    ),
)
async def update_preferences(
    run_context: RunContext,
    patch: dict[str, Any],
) -> dict[str, Any]:
    user_id = run_context.user_id
    async with with_user_session(UUID(user_id)) as session:
        from src.universe.application.use_cases import SetCareerPreferences
        from src.universe.infrastructure.repositories import (
            SqlAlchemyCareerPreferencesRepository,
        )

        uc = SetCareerPreferences(SqlAlchemyCareerPreferencesRepository(session))
        result = await uc.execute(user_id=user_id, patch=patch)
        return {"ok": True, "preferences": result}


@require_user_id
@tool(
    name="dismiss_reminder",
    description=(
        "Dismiss a reminder by id (cert expiring, course stale, etc.). The "
        "reminder is not deleted — it stays in the audit trail but won't "
        "appear in `list_reminders` anymore."
    ),
)
async def dismiss_reminder(
    run_context: RunContext,
    reminder_id: str,
) -> dict[str, Any]:
    user_id = run_context.user_id
    async with with_user_session(UUID(user_id)) as session:
        from src.universe.application.reminders import DismissReminder

        result = await DismissReminder(session).execute(
            user_id=user_id, reminder_id=reminder_id
        )
        if result.is_failure:
            return {"ok": False, "error": str(result.error)}
        return {"ok": True}


@require_user_id
@tool(
    name="set_job_status",
    description=(
        "Move a job to a new status (kanban transition). `new_status` must be "
        "one of: interested, applied, interviewing, offer, rejected, archived. "
        "When moving to 'applied' for the first time, `applied_at` is stamped "
        "automatically. Returns the updated job row."
    ),
)
async def set_job_status(
    run_context: RunContext,
    job_id: str,
    new_status: str,
) -> dict[str, Any]:
    user_id = run_context.user_id
    if new_status not in VALID_JOB_STATUSES:
        return {"ok": False, "error": f"invalid status '{new_status}'"}

    from src.documents.infrastructure.orm import JobOrm

    async with with_user_session(UUID(user_id)) as session:
        try:
            row = await session.get(JobOrm, UUID(job_id))
        except ValueError:
            return {"ok": False, "error": "invalid job_id"}
        if row is None or str(row.user_id) != user_id:
            return {"ok": False, "error": "not_found"}
        parsed = dict(row.description_parsed or {})
        tracker = dict(parsed.get("_tracker", {}) or {})
        tracker["status"] = new_status
        if new_status == "applied" and not tracker.get("applied_at"):
            tracker["applied_at"] = datetime.now(UTC).isoformat()
        parsed["_tracker"] = tracker
        row.description_parsed = parsed
        return {
            "ok": True,
            "job": {
                "id": str(row.id),
                "status": new_status,
                "title": row.title,
                "company_name": row.company_name,
                "applied_at": tracker.get("applied_at"),
            },
        }


@require_user_id
@tool(
    name="compute_job_match",
    description=(
        "Compute (or recompute) the match score between a job's description "
        "and the user's universe. Cached on the job row. Returns the new "
        "match_score (0-100). Use before `present_job_match` when you want "
        "fresh numbers; the JD must be long enough (>30 chars)."
    ),
)
async def compute_job_match(
    run_context: RunContext,
    job_id: str,
) -> dict[str, Any]:
    user_id = run_context.user_id

    from src.documents.infrastructure.orm import JobOrm
    from src.shared.embeddings import get_embeddings_service
    from src.universe.infrastructure.semantic_search import PgVectorSemanticSearch

    async with with_user_session(UUID(user_id)) as session:
        try:
            row = await session.get(JobOrm, UUID(job_id))
        except ValueError:
            return {"ok": False, "error": "invalid job_id"}
        if row is None or str(row.user_id) != user_id:
            return {"ok": False, "error": "not_found"}
        if not row.description_raw or len(row.description_raw) < 30:
            return {"ok": False, "error": "missing_description"}

        embedder = get_embeddings_service()
        search = PgVectorSemanticSearch(session)
        vec = await embedder.embed(row.description_raw)
        retrieved = await search.search(user_id=row.user_id, embedding=vec, top_k=20)
        avg = (
            sum(r["score"] for r in retrieved) / len(retrieved) if retrieved else 0.0
        )
        match_score = int(round(max(0.0, min(1.0, (avg + 1) / 2)) * 100))

        parsed = dict(row.description_parsed or {})
        tracker = dict(parsed.get("_tracker", {}) or {})
        tracker["match_score"] = match_score
        parsed["_tracker"] = tracker
        row.description_parsed = parsed
        return {
            "ok": True,
            "job_id": job_id,
            "match_score": match_score,
            "title": row.title,
            "company_name": row.company_name,
        }
