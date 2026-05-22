"""Server-side tools for `interview_prep_specialist`.

The specialist itself crafts the Q&A from JD + profile context using its LLM.
This module only provides DATA-FETCH helpers it can call:

  - `get_job_for_interview(job_id)`: full JD + status from the job tracker
  - `get_interview_context_blob()`: compact stringified summary of the user's
     universe (skills + recent experiences + projects) — fed to the LLM in
     one go so it can write tailored questions/tips.

The specialist then calls `present_widget(kind='interview_qa', ...)` with
the Q&A list it composed. Persistence: the Q&A is also written as a note
with tag `interview_prep:<company_slug>` so the user can re-read later.
"""
from __future__ import annotations

from datetime import date as _date
from typing import Any
from uuid import UUID

from agno.run.base import RunContext
from agno.tools import tool
from sqlalchemy import select

from src.shared.db import get_session_factory, set_rls_user
from src.universe.infrastructure.orm import (
    ExperienceOrm,
    ProjectOrm,
    SkillOrm,
    UniverseOrm,
)


@tool(
    name="get_job_for_interview",
    description=(
        "Fetch a job from the user's tracker by id. Returns "
        "{title, company_name, description_raw, url, status, location}. "
        "Use this when the user mentions an interview for a job that's "
        "already saved ('tengo entrevista en Stripe' and Stripe is in the "
        "kanban). If the job isn't found, return ok=false and the specialist "
        "should ask the user to paste the JD instead."
    ),
)
async def get_job_for_interview(
    run_context: RunContext,
    job_id: str,
) -> dict[str, Any]:
    user_id = run_context.user_id
    if not user_id:
        return {"ok": False, "error": "missing user_id"}
    from src.documents.infrastructure.orm import JobOrm  # local import to avoid cycles

    factory = get_session_factory()
    async with factory() as session:
        await set_rls_user(session, UUID(user_id))
        row = (
            await session.execute(
                select(JobOrm)
                .where(JobOrm.id == UUID(job_id))
                .where(JobOrm.user_id == UUID(user_id))
            )
        ).scalar_one_or_none()
        if row is None:
            return {"ok": False, "error": "job not found"}
        return {
            "ok": True,
            "job": {
                "id": str(row.id),
                "title": row.title,
                "company_name": row.company_name,
                "description_raw": getattr(row, "description_raw", None),
                "url": getattr(row, "url", None),
                "status": row.status,
                "location": getattr(row, "location", None),
            },
        }


@tool(
    name="get_interview_context_blob",
    description=(
        "Return a compact text blob summarizing the user's universe (headline, "
        "top-5 recent experiences, top-10 skills with level, top-5 projects "
        "with tech_stack). Use ONCE per interview-prep turn to ground the "
        "Q&A you'll generate. Result is a single string ≤ ~1500 chars."
    ),
)
async def get_interview_context_blob(run_context: RunContext) -> dict[str, Any]:
    user_id = run_context.user_id
    if not user_id:
        return {"ok": False, "error": "missing user_id"}
    user_uuid = UUID(user_id)
    factory = get_session_factory()
    parts: list[str] = []
    async with factory() as session:
        await set_rls_user(session, user_uuid)
        uni = (
            await session.execute(
                select(UniverseOrm).where(UniverseOrm.user_id == user_uuid)
            )
        ).scalar_one_or_none()
        if uni and (uni.headline or "").strip():
            parts.append(f"HEADLINE: {uni.headline.strip()}")
        # Experiences — last 5 by start_date desc
        exps = (
            await session.execute(
                select(ExperienceOrm)
                .where(ExperienceOrm.user_id == user_uuid)
                .order_by(ExperienceOrm.start_date.desc().nulls_last())
                .limit(5)
            )
        ).scalars().all()
        if exps:
            parts.append("EXPERIENCIA:")
            for e in exps:
                start = e.start_date.isoformat() if e.start_date else "?"
                end = (
                    "actual"
                    if getattr(e, "is_current", False) or not e.end_date
                    else e.end_date.isoformat()
                )
                parts.append(f"- {e.role or '?'} @ {e.organization or '?'} ({start} → {end})")
        # Skills — top 10 by years desc, level desc
        skills = (
            await session.execute(
                select(SkillOrm)
                .where(SkillOrm.user_id == user_uuid)
                .order_by(SkillOrm.years.desc().nulls_last())
                .limit(10)
            )
        ).scalars().all()
        if skills:
            parts.append("SKILLS:")
            for s in skills:
                lv = s.level or "?"
                y = f"{s.years}a" if s.years else "?"
                parts.append(f"- {s.name} · {lv} · {y}")
        # Projects — top 5 most recent
        projs = (
            await session.execute(
                select(ProjectOrm)
                .where(ProjectOrm.user_id == user_uuid)
                .order_by(ProjectOrm.start_date.desc().nulls_last())
                .limit(5)
            )
        ).scalars().all()
        if projs:
            parts.append("PROYECTOS:")
            for p in projs:
                stack = ", ".join(p.tech_stack or [])
                parts.append(f"- {p.name}: {p.description or ''} [{stack}]")
    blob = "\n".join(parts) if parts else "(universo vacío)"
    return {"ok": True, "blob": blob, "today": _date.today().isoformat()}
