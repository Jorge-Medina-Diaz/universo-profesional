"""Server-side tools for `insights_specialist`.

Two helpers:
  - `compute_profile_health`: scans the user's universe and returns a
    completeness + freshness + coverage score (0..100) plus a short list of
    actionable recommendations.
  - `detect_software_area`: thin wrapper around `shape_service` that
    returns the top-confidence area for legacy callers. New code should
    use `get_universe_shape` (full T/π-shape) instead.

Both are READ-ONLY. The canonical area keyword map now lives in
`src.universe.application.area_keywords` so the foundation (shape_service)
and the agents share a single source of truth.
"""
from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

from agno.run.base import RunContext
from agno.tools import tool
from sqlalchemy import func, select

from src.agents.tools._deps import require_user_id
from src.shared.db import with_user_session
from src.universe.application.shape_service import (
    compute_area_strengths,
    load_area_strengths,
    primary_area_from_strengths,
)
from src.universe.infrastructure.orm import (
    AchievementOrm,
    CertificationOrm,
    CourseOrm,
    EducationOrm,
    ExperienceOrm,
    InterestOrm,
    LanguageOrm,
    ProjectOrm,
    SkillOrm,
    UniverseOrm,
)

# Weight distribution for the health score — sums to 100.
WEIGHTS = {
    "header": 10,        # universes.headline + name
    "experience": 25,    # at least 1 role, ideally 2+
    "skills": 20,        # >= 5 skills
    "education": 8,
    "projects": 10,
    "languages": 5,
    "certifications": 5,
    "achievements": 5,
    "interests": 2,
    "freshness": 10,     # recent updates
}

STALE_DAYS = 90  # if nothing updated in 90d, freshness suffers


def _now_utc() -> datetime:
    return datetime.now(UTC)


async def _count_rows(session, table, user_uuid: UUID) -> int:
    result = await session.execute(
        select(func.count())
        .select_from(table)
        .where(table.user_id == user_uuid)
        .where(table.deleted_at.is_(None))
    )
    return result.scalar_one()


def _bonus(have: int, target: int) -> float:
    if have <= 0:
        return 0.0
    if have >= target:
        return 1.0
    return have / target


@require_user_id
@tool(
    name="compute_profile_health",
    description=(
        "Compute the user's profile health: a 0..100 score + a list of "
        "actionable recommendations (e.g. 'add at least one project', 'your "
        "skills section is stale — last updated 6 months ago'). Read-only. "
        "Call this when the user asks 'how complete is my profile' or for a "
        "quarterly review trigger."
    ),
)
async def compute_profile_health(run_context: RunContext) -> dict[str, Any]:
    user_id = run_context.user_id
    user_uuid = UUID(user_id)
    async with with_user_session(user_uuid) as session:
        # Header (UniverseOrm)
        uni = (
            await session.execute(
                select(UniverseOrm).where(UniverseOrm.user_id == user_uuid)
            )
        ).scalar_one_or_none()
        # Counts
        n_exp = await _count_rows(session, ExperienceOrm, user_uuid)
        n_skills = await _count_rows(session, SkillOrm, user_uuid)
        n_edu = await _count_rows(session, EducationOrm, user_uuid)
        n_proj = await _count_rows(session, ProjectOrm, user_uuid)
        n_lang = await _count_rows(session, LanguageOrm, user_uuid)
        n_cert = await _count_rows(session, CertificationOrm, user_uuid)
        n_ach = await _count_rows(session, AchievementOrm, user_uuid)
        n_int = await _count_rows(session, InterestOrm, user_uuid)
        n_course = await _count_rows(session, CourseOrm, user_uuid)
        # Freshness: did anything update in the last STALE_DAYS?
        stale_cutoff = _now_utc() - timedelta(days=STALE_DAYS)
        latest_update = uni.updated_at if uni else None
        for table in (
            ExperienceOrm,
            SkillOrm,
            ProjectOrm,
            EducationOrm,
            CourseOrm,
            LanguageOrm,
            CertificationOrm,
            AchievementOrm,
        ):
            row = (
                await session.execute(
                    select(table.updated_at)
                    .where(table.user_id == user_uuid)
                    .order_by(table.updated_at.desc())
                    .limit(1)
                )
            ).scalar_one_or_none()
            if row and (latest_update is None or row > latest_update):
                latest_update = row
        is_fresh = latest_update is not None and latest_update >= stale_cutoff

    # Score breakdown
    parts: dict[str, float] = {
        "header": (
            WEIGHTS["header"]
            if uni and (uni.headline or "").strip()
            else 0
        ),
        "experience": WEIGHTS["experience"] * _bonus(n_exp, 2),
        "skills": WEIGHTS["skills"] * _bonus(n_skills, 6),
        "education": WEIGHTS["education"] * _bonus(n_edu, 1),
        "projects": WEIGHTS["projects"] * _bonus(n_proj, 2),
        "languages": WEIGHTS["languages"] * _bonus(n_lang, 1),
        "certifications": WEIGHTS["certifications"] * _bonus(n_cert, 1),
        "achievements": WEIGHTS["achievements"] * _bonus(n_ach, 1),
        "interests": WEIGHTS["interests"] * _bonus(n_int, 1),
        "freshness": WEIGHTS["freshness"] if is_fresh else 0,
    }
    total = round(sum(parts.values()))

    recs: list[dict[str, str]] = []
    if parts["header"] == 0:
        recs.append({"kind": "header", "label": "Falta el headline — una frase que resuma quién eres."})
    if n_exp == 0:
        recs.append({"kind": "experience", "label": "Aún no hay experiencia laboral. Empieza por tu puesto actual."})
    elif n_exp < 2:
        recs.append({"kind": "experience", "label": "Sólo 1 experiencia — añadir otra refuerza tu trayectoria."})
    if n_skills < 5:
        recs.append({"kind": "skills", "label": f"Sólo {n_skills} skills — apunta al menos a 5-8."})
    if n_proj < 2:
        recs.append({"kind": "projects", "label": "Faltan proyectos. Aporta evidencia tangible de lo que sabes hacer."})
    if n_lang == 0:
        recs.append({"kind": "languages", "label": "Sin idiomas registrados. Importante para recruiters internacionales."})
    if not is_fresh:
        days_stale = (
            (_now_utc() - latest_update).days if latest_update else None
        )
        if days_stale:
            recs.append({
                "kind": "freshness",
                "label": f"Hace {days_stale} días sin actualizar nada. Cuenta lo nuevo.",
            })
        else:
            recs.append({"kind": "freshness", "label": "Universo recién creado, vamos llenándolo."})

    return {
        "ok": True,
        "score": total,
        "breakdown": {k: round(v, 1) for k, v in parts.items()},
        "counts": {
            "experience": n_exp,
            "skills": n_skills,
            "education": n_edu,
            "projects": n_proj,
            "languages": n_lang,
            "certifications": n_cert,
            "achievements": n_ach,
            "interests": n_int,
            "courses": n_course,
        },
        "is_fresh": is_fresh,
        "last_update_iso": latest_update.isoformat() if latest_update else None,
        "recommendations": recs,
    }


@require_user_id
@tool(
    name="detect_software_area",
    description=(
        "Detect the user's primary software area (backend|frontend|"
        "fullstack|devops|cloud|mobile|ai_ml|llm_agents|data_eng|security|"
        "platform|none) from their universe. Returns {primary, confidence, "
        "secondary}. This is a thin wrapper around the shape persistence; "
        "prefer `get_universe_shape` if you need the full T/π-shape "
        "breakdown."
    ),
)
async def detect_software_area(run_context: RunContext) -> dict[str, Any]:
    user_id = run_context.user_id
    user_uuid = UUID(user_id)
    async with with_user_session(user_uuid) as session:
        strengths, _primary, _secondary = await load_area_strengths(session, user_uuid)
        if not strengths:
            # Cache miss → compute on the fly (cold path).
            result = await compute_area_strengths(session, user_uuid)
            strengths = result.strengths
    if not strengths:
        return {
            "ok": True,
            "primary": "none",
            "confidence": 0.0,
            "secondary": None,
            "evidence_count": 0,
        }
    primary, confidence, secondary = primary_area_from_strengths(strengths)
    return {
        "ok": True,
        "primary": primary,
        "confidence": confidence,
        "secondary": secondary,
        "evidence_count": next(
            (s.breadth_count for s in strengths if s.area == primary), 0
        ),
        "all_scores": {s.area: s.confidence for s in strengths},
    }
