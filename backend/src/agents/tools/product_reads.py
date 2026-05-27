"""Product reads — the agent's eyes on jobs, documents, preferences, reminders, integrations, tier.

These tools are read-only, RLS-scoped, and exposed to the coordinator and the
two proactive specialists (`job_strategist`, `cv_coach`). They deliberately
return *compact* shapes (top-N items, key fields only) so the LLM doesn't
exhaust its context window with structured data dumps — full detail is one
follow-up call away if needed.

Kept separate from `universe_reads.py` (which is universe-entity-centric:
summary, gaps, search). This file is about *product surface* the user already
interacts with via the rest of the app.
"""
from __future__ import annotations

from typing import Any
from uuid import UUID

from agno.run.base import RunContext
from agno.tools import tool

from src.agents.tools._deps import require_user_id
from src.shared.db import with_user_session


@require_user_id
@tool(
    name="list_jobs",
    description=(
        "List the user's job-tracker entries (the kanban). Optional `status` "
        "filter accepts one of: interested, applied, interviewing, offer, "
        "rejected, archived. `limit` defaults to 20. Returns compact rows: "
        "id, title, company_name, status, match_score, applied_at, url, "
        "description_preview (first 240 chars), position."
    ),
)
async def list_jobs(
    run_context: RunContext,
    status: str | None = None,
    limit: int = 20,
) -> dict[str, Any]:
    user_id = run_context.user_id
    from sqlalchemy import desc, select

    from src.documents.infrastructure.orm import JobOrm

    async with with_user_session(UUID(user_id)) as session:
        stmt = (
            select(JobOrm)
            .where(JobOrm.user_id == UUID(user_id))
            .order_by(desc(JobOrm.created_at))
            .limit(min(max(limit, 1), 100))
        )
        rows = (await session.execute(stmt)).scalars().all()
        items: list[dict[str, Any]] = []
        for r in rows:
            tracker = dict((r.description_parsed or {}).get("_tracker", {}) or {})
            row_status = tracker.get("status", "interested")
            if status and row_status != status:
                continue
            desc_raw = r.description_raw or ""
            items.append(
                {
                    "id": str(r.id),
                    "title": r.title,
                    "company_name": r.company_name,
                    "url": r.url,
                    "status": row_status,
                    "match_score": tracker.get("match_score"),
                    "applied_at": tracker.get("applied_at"),
                    "position": tracker.get("position"),
                    "description_preview": desc_raw[:240] + ("…" if len(desc_raw) > 240 else ""),
                    "has_description": len(desc_raw) > 30,
                    "created_at": r.created_at.isoformat() if r.created_at else None,
                }
            )
        return {"count": len(items), "items": items}


@require_user_id
@tool(
    name="list_documents",
    description=(
        "List generated documents (CVs + cover letters). Optional `kind` "
        "filter accepts 'cv' or 'cover_letter'. `limit` defaults to 10. "
        "Returns: id, kind, template, language, tone, created_at, "
        "has_pdf, has_docx, share_token, job_id (when generated from a job)."
    ),
)
async def list_documents(
    run_context: RunContext,
    kind: str | None = None,
    limit: int = 10,
) -> dict[str, Any]:
    user_id = run_context.user_id
    from sqlalchemy import desc, select

    from src.documents.infrastructure.orm import DocumentOrm

    async with with_user_session(UUID(user_id)) as session:
        stmt = (
            select(DocumentOrm)
            .where(DocumentOrm.user_id == UUID(user_id))
            .order_by(desc(DocumentOrm.created_at))
            .limit(min(max(limit, 1), 50))
        )
        if kind:
            stmt = stmt.where(DocumentOrm.kind == kind)
        rows = (await session.execute(stmt)).scalars().all()
        return {
            "count": len(rows),
            "items": [
                {
                    "id": str(r.id),
                    "kind": r.kind,
                    "template": r.template,
                    "language": r.language,
                    "tone": r.tone,
                    "created_at": r.created_at.isoformat() if r.created_at else None,
                    "has_pdf": bool(r.pdf_path),
                    "has_docx": bool(r.docx_path),
                    "share_token": r.share_token,
                    "job_id": str(r.job_id) if r.job_id else None,
                }
                for r in rows
            ],
        }


@require_user_id
@tool(
    name="get_preferences",
    description=(
        "Return the user's career preferences: target status, salary range "
        "+ currency, contract types, remote preference, relocation, working "
        "areas, perks (must-have / nice-to-have), preferred / discarded "
        "competences and roles, motivations. Returns null if never set."
    ),
)
async def get_preferences(run_context: RunContext) -> dict[str, Any] | None:
    user_id = run_context.user_id
    async with with_user_session(UUID(user_id)) as session:
        from src.universe.application.use_cases import GetCareerPreferences
        from src.universe.infrastructure.repositories import (
            SqlAlchemyCareerPreferencesRepository,
        )

        uc = GetCareerPreferences(SqlAlchemyCareerPreferencesRepository(session))
        return await uc.execute(user_id=user_id)


@require_user_id
@tool(
    name="list_reminders",
    description=(
        "List active (non-dismissed) reminders: certs expiring, courses gone "
        "stale, entries marked for review. Optional `due_within_days` filter "
        "(e.g. 30 to see what's due in the next month). `limit` defaults to 20."
    ),
)
async def list_reminders(
    run_context: RunContext,
    due_within_days: int | None = None,
    limit: int = 20,
) -> dict[str, Any]:
    user_id = run_context.user_id
    async with with_user_session(UUID(user_id)) as session:
        from src.universe.application.reminders import ListReminders

        items = await ListReminders(session).execute(
            user_id=user_id,
            due_within_days=due_within_days,
            limit=min(max(limit, 1), 100),
        )
        return {"count": len(items), "items": items}


@require_user_id
@tool(
    name="get_integrations_status",
    description=(
        "Return the user's connected external accounts (GitHub, LinkedIn, "
        "etc.). For each: provider, username, scopes, connected_at, "
        "last_synced_at, sync_status. Useful when the user asks about their "
        "sync state or you want to suggest a re-sync."
    ),
)
async def get_integrations_status(run_context: RunContext) -> dict[str, Any]:
    user_id = run_context.user_id
    async with with_user_session(UUID(user_id)) as session:
        from src.integrations.application.connect_disconnect import ListConnections
        from src.integrations.infrastructure.repositories import (
            SqlExternalAccountRepository,
        )

        uc = ListConnections(SqlExternalAccountRepository(session))
        connections = await uc.execute(user_id=user_id)
        return {"connections": connections, "count": len(connections)}


@require_user_id
@tool(
    name="get_tier",
    description=(
        "Return the user's current subscription tier ('free' or 'pro') and "
        "is_pro flag. Use to gate suggestions of PRO-only features like "
        "Bright Data LinkedIn sync."
    ),
)
async def get_tier(run_context: RunContext) -> dict[str, Any]:
    user_id = run_context.user_id
    async with with_user_session(UUID(user_id)) as session:
        from src.identity.infrastructure.repositories import SqlAlchemyUserRepository

        repo = SqlAlchemyUserRepository(session)
        user = await repo.get_by_id(UUID(user_id))
        if user is None:
            return {"error": "user not found"}
        return {"tier": user.tier, "is_pro": user.is_pro}
