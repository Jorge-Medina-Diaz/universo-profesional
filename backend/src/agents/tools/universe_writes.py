"""Server-side upsert tools — every agent write goes through the coherence engine.

Each tool:
  1. Pulls `user_id` from the Agno `RunContext` (set by the AGUI handler from
     the JWT — never trust the client).
  2. Opens a fresh AsyncSession + RLS scope.
  3. Calls `UpsertUniverseEntity.execute(...)` which finds existing entries,
     merges by declarative rules, records a `universe_change_log` row per
     field change, and auto-links evidence for skills derived from other
     entities.

The agent never sees the underlying `add_*` paths; if the engine can't decide
whether to merge or create, it emits a suggestion and the result includes
`status='suggested'` for the chat layer to render a DiffCard.
"""
from __future__ import annotations

from typing import Any
from uuid import UUID

from agno.run.base import RunContext
from agno.tools import tool

from src.coherence.application.upsert_use_cases import UpsertUniverseEntity
from src.coherence.infrastructure.change_log_repo import SqlAlchemyChangeLogRepository
from src.coherence.infrastructure.semantic_matcher import PgVectorSemanticMatcher
from src.shared.db import with_user_session
from src.shared.uow import UnitOfWork


def _strip_none(**kwargs: Any) -> dict[str, Any]:
    return {k: v for k, v in kwargs.items() if v is not None}


async def _run_upsert(
    *,
    run_context: RunContext,
    entity_type: str,
    payload: dict[str, Any],
) -> dict[str, Any]:
    user_id = run_context.user_id
    if not user_id:
        return {"ok": False, "error": "missing user_id"}

    async with with_user_session(UUID(user_id)) as session:
        change_log = SqlAlchemyChangeLogRepository(session)
        matcher = PgVectorSemanticMatcher(session)
        uc = UpsertUniverseEntity(
            session, change_log=change_log, semantic_matcher=matcher
        )
        uow = UnitOfWork(session)
        outcome = await uc.execute(
            entity_type=entity_type,
            user_id=user_id,
            payload=payload,
            uow=uow,
            source="agent_chat",
            agent_run_id=run_context.run_id,
        )
        await uow.commit()
        return {
            "ok": outcome.status.value != "noop"
            or outcome.entity_id is not None,
            "status": outcome.status.value,
            "entity_id": str(outcome.entity_id) if outcome.entity_id else None,
            "diffs": [
                {"field": d.field, "old": _jsonify(d.old), "new": _jsonify(d.new)}
                for d in outcome.diffs
            ],
            "suggestion_id": str(outcome.suggestion_id)
            if outcome.suggestion_id
            else None,
            "reason": outcome.reason,
        }


def _jsonify(v: Any) -> Any:
    from datetime import date, datetime
    from uuid import UUID as _UUID

    if isinstance(v, (datetime, date)):
        return v.isoformat()
    if isinstance(v, _UUID):
        return str(v)
    if isinstance(v, list):
        return [_jsonify(x) for x in v]
    return v


# --- Per-entity upsert tools ------------------------------------------------


@tool(
    name="upsert_experience",
    description=(
        "Persist or merge a work-experience entry. The engine searches for an "
        "existing entry by org+role; if found, merges (end_date max, highlights "
        "union, …) and logs the diff. If new, creates."
    ),
)
async def upsert_experience(
    run_context: RunContext,
    organization: str,
    role: str,
    start_date: str | None = None,
    end_date: str | None = None,
    is_current: bool | None = None,
    description: str | None = None,
    highlights: list[str] | None = None,
    competences: list[str] | None = None,
) -> dict[str, Any]:
    return await _run_upsert(
        run_context=run_context,
        entity_type="experience",
        payload=_strip_none(
            organization=organization,
            role=role,
            start_date=start_date,
            end_date=end_date,
            is_current=is_current,
            description=description,
            highlights=highlights,
            competences=competences,
        ),
    )


@tool(
    name="upsert_education",
    description="Persist or merge an education entry.",
)
async def upsert_education(
    run_context: RunContext,
    institution: str,
    degree: str | None = None,
    field_of_study: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    is_current: bool | None = None,
    description: str | None = None,
    highlights: list[str] | None = None,
) -> dict[str, Any]:
    return await _run_upsert(
        run_context=run_context,
        entity_type="education",
        payload=_strip_none(
            institution=institution,
            degree=degree,
            field_of_study=field_of_study,
            start_date=start_date,
            end_date=end_date,
            is_current=is_current,
            description=description,
            highlights=highlights,
        ),
    )


@tool(
    name="upsert_project",
    description="Persist or merge a project entry.",
)
async def upsert_project(
    run_context: RunContext,
    name: str,
    description: str | None = None,
    role: str | None = None,
    project_type: str | None = None,
    tech_stack: list[str] | None = None,
    highlights: list[str] | None = None,
    impact: str | None = None,
    url: str | None = None,
    is_current: bool | None = None,
    status: str | None = None,
) -> dict[str, Any]:
    return await _run_upsert(
        run_context=run_context,
        entity_type="project",
        payload=_strip_none(
            name=name,
            description=description,
            role=role,
            project_type=project_type,
            tech_stack=tech_stack,
            highlights=highlights,
            impact=impact,
            url=url,
            is_current=is_current,
            status=status,
        ),
    )


@tool(
    name="upsert_skill",
    description=(
        "Persist or merge a skill entry. Accepts optional `derived_from_*` ids "
        "(project, experience, course, certification, achievement, note) to "
        "auto-create an evidence link in the universe graph."
    ),
)
async def upsert_skill(
    run_context: RunContext,
    name: str,
    category: str | None = None,
    level: str | None = None,
    years: int | None = None,
    last_used_year: int | None = None,
    derived_from_project_id: str | None = None,
    derived_from_experience_id: str | None = None,
    derived_from_course_id: str | None = None,
    derived_from_certification_id: str | None = None,
    derived_from_achievement_id: str | None = None,
    mentioned_in_note_id: str | None = None,
) -> dict[str, Any]:
    return await _run_upsert(
        run_context=run_context,
        entity_type="skill",
        payload=_strip_none(
            name=name,
            category=category or "hard",
            level=level,
            years=years,
            last_used_year=last_used_year,
            derived_from_project_id=derived_from_project_id,
            derived_from_experience_id=derived_from_experience_id,
            derived_from_course_id=derived_from_course_id,
            derived_from_certification_id=derived_from_certification_id,
            derived_from_achievement_id=derived_from_achievement_id,
            mentioned_in_note_id=mentioned_in_note_id,
        ),
    )


@tool(
    name="upsert_certification",
    description="Persist or merge a certification entry.",
)
async def upsert_certification(
    run_context: RunContext,
    name: str,
    issuer: str | None = None,
    issued_on: str | None = None,
    expires_on: str | None = None,
    credential_id: str | None = None,
    verification_url: str | None = None,
) -> dict[str, Any]:
    return await _run_upsert(
        run_context=run_context,
        entity_type="certification",
        payload=_strip_none(
            name=name,
            issuer=issuer,
            issued_on=issued_on,
            expires_on=expires_on,
            credential_id=credential_id,
            verification_url=verification_url,
        ),
    )


@tool(
    name="upsert_course",
    description="Persist or merge a course entry.",
)
async def upsert_course(
    run_context: RunContext,
    title: str,
    platform: str | None = None,
    started_on: str | None = None,
    completed_on: str | None = None,
    duration_hours: int | None = None,
    certificate_url: str | None = None,
) -> dict[str, Any]:
    return await _run_upsert(
        run_context=run_context,
        entity_type="course",
        payload=_strip_none(
            title=title,
            platform=platform,
            started_on=started_on,
            completed_on=completed_on,
            duration_hours=duration_hours,
            certificate_url=certificate_url,
        ),
    )


@tool(
    name="upsert_language",
    description="Persist or merge a language entry (ISO-639-1 + CEFR).",
)
async def upsert_language(
    run_context: RunContext,
    code: str,
    name: str,
    level: str,
    certification: str | None = None,
) -> dict[str, Any]:
    return await _run_upsert(
        run_context=run_context,
        entity_type="language",
        payload=_strip_none(
            code=code, name=name, level=level, certification=certification
        ),
    )


@tool(
    name="upsert_achievement",
    description="Persist or merge an achievement / award / publication / patent.",
)
async def upsert_achievement(
    run_context: RunContext,
    title: str,
    achieved_on: str | None = None,
    description: str | None = None,
    context: str | None = None,
    evidence_url: str | None = None,
) -> dict[str, Any]:
    return await _run_upsert(
        run_context=run_context,
        entity_type="achievement",
        payload=_strip_none(
            title=title,
            achieved_on=achieved_on,
            description=description,
            context=context,
            evidence_url=evidence_url,
        ),
    )


@tool(
    name="upsert_interest",
    description="Persist or merge a professional or personal interest entry.",
)
async def upsert_interest(
    run_context: RunContext,
    name: str,
    description: str | None = None,
) -> dict[str, Any]:
    return await _run_upsert(
        run_context=run_context,
        entity_type="interest",
        payload=_strip_none(name=name, description=description),
    )
