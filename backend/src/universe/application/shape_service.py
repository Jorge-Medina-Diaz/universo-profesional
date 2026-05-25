"""Compute polyglot shape from a user's universe.

The single source of truth for area persistence. Reads skills + projects
+ experiences, scores each against canonical area keywords, aggregates
per-(user, area) into depth/breadth/recency/confidence, and upserts the
results to `area_strengths` (plus a cached primary/secondary on
`universes`).

`shape_type` is inferred from the distribution of confidences:
  - "none"  → no evidence
  - "I"     → one area dominates (≥60% of total signal)
  - "T"     → one primary area + ≥2 broad areas
  - "π"     → exactly 2 primary areas (frontend+backend → fullstack)
  - "M"     → 3+ primary areas (true polyglot, possibly diluted)

This module is read-only over Skill/Project/Experience and write-only
over AreaStrength + UniverseOrm (the cached projection).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.universe.application.area_keywords import (
    FRONT_BACK_PAIR,
    SOFTWARE_AREA_KEYWORDS,
    area_hits_per_kw,
    collect_text_blob,
    primary_area,
    score_areas,
)
from src.universe.domain.entities import AreaStrength, ShapeType
from src.universe.infrastructure.orm import (
    ExperienceOrm,
    ProjectOrm,
    SkillOrm,
    UniverseOrm,
)
from src.universe.infrastructure.repositories import (
    SqlAlchemyAreaStrengthRepository,
    update_universe_areas,
)


@dataclass
class ShapeResult:
    user_id: UUID
    strengths: list[AreaStrength] = field(default_factory=list)
    primary_areas: list[str] = field(default_factory=list)
    secondary_areas: list[str] = field(default_factory=list)
    shape_type: ShapeType = "none"
    computed_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


CURRENT_YEAR = datetime.now(timezone.utc).year


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _months_since(year: int | None) -> int | None:
    if year is None or year <= 0:
        return None
    now = _now_utc()
    delta_years = now.year - year
    return max(0, delta_years * 12 + now.month - 1)


async def _load_universe_blob(
    session: AsyncSession, user_id: UUID
) -> tuple[list[SkillOrm], list[ProjectOrm], list[ExperienceOrm]]:
    skills = (
        await session.execute(
            select(SkillOrm)
            .where(SkillOrm.user_id == user_id)
            .where(SkillOrm.deleted_at.is_(None))
        )
    ).scalars().all()
    projects = (
        await session.execute(
            select(ProjectOrm)
            .where(ProjectOrm.user_id == user_id)
            .where(ProjectOrm.deleted_at.is_(None))
        )
    ).scalars().all()
    experiences = (
        await session.execute(
            select(ExperienceOrm)
            .where(ExperienceOrm.user_id == user_id)
            .where(ExperienceOrm.deleted_at.is_(None))
        )
    ).scalars().all()
    return list(skills), list(projects), list(experiences)


def _experience_years(exp: ExperienceOrm) -> float:
    """Approximate years between start_date and end_date (or today)."""
    if exp.start_date is None:
        return 0.0
    end = exp.end_date or _now_utc().date()
    delta_days = (end - exp.start_date).days
    if delta_days <= 0:
        return 0.0
    return round(delta_days / 365.25, 2)


def _classify_skill_areas(name: str, category: str) -> list[str]:
    blob = collect_text_blob([name, category])
    return list(score_areas(blob).keys())


def _classify_project_areas(p: ProjectOrm) -> list[str]:
    stack = " ".join(str(s) for s in (p.tech_stack or []))
    blob = collect_text_blob([p.name, p.description, stack])
    return list(score_areas(blob).keys())


def _classify_experience_areas(e: ExperienceOrm) -> list[str]:
    comp = " ".join(str(c) for c in (e.competences or []))
    hl = " ".join(str(h) for h in (e.highlights or []))
    blob = collect_text_blob([e.role, e.description, comp, hl])
    return list(score_areas(blob).keys())


def _confidence(breadth: int, recency_months: int | None) -> float:
    """Map breadth + recency to a 0..1 score.

    Breadth alone: log-shaped saturation around 8 hits.
    Recency penalty: linear from 0 (fresh) to 0.4 (>=4 years).
    """
    if breadth <= 0:
        return 0.0
    # base from breadth: 1 - 0.5^(breadth/4) → 0.16@1, 0.5@4, 0.84@10
    import math

    base = 1 - math.pow(0.5, breadth / 4.0)
    penalty = 0.0
    if recency_months is not None:
        years = recency_months / 12.0
        penalty = min(0.4, max(0.0, (years - 1) * 0.1))
    return round(max(0.0, min(1.0, base - penalty)), 2)


def _infer_shape(scores: dict[str, float], primary_areas: list[str]) -> ShapeType:
    n_primary = len(primary_areas)
    if not scores or n_primary == 0:
        return "none"
    total = sum(scores.values()) or 1.0
    top = max(scores.values())
    top_ratio = top / total
    n_broad = sum(1 for v in scores.values() if v >= 0.2)
    if n_primary == 1:
        if top_ratio >= 0.6 and n_broad <= 1:
            return "I"
        return "T"
    if n_primary == 2:
        return "π"
    return "M"


async def compute_area_strengths(
    session: AsyncSession,
    user_id: UUID,
) -> ShapeResult:
    skills, projects, experiences = await _load_universe_blob(session, user_id)

    # 1. Tally evidence per area + collect (year_signal, depth_signal)
    per_area: dict[str, dict[str, Any]] = {}

    def _register(area: str, *, recency_year: int | None, depth_years: float | None) -> None:
        slot = per_area.setdefault(
            area,
            {"breadth": 0, "max_year": None, "max_depth_years": 0.0},
        )
        slot["breadth"] += 1
        if recency_year is not None:
            if slot["max_year"] is None or recency_year > slot["max_year"]:
                slot["max_year"] = recency_year
        if depth_years is not None and depth_years > slot["max_depth_years"]:
            slot["max_depth_years"] = depth_years

    # Skills
    for s in skills:
        areas = _classify_skill_areas(s.name, s.category)
        for area in areas:
            _register(
                area,
                recency_year=s.last_used_year,
                depth_years=float(s.years) if s.years else None,
            )

    # Projects
    for p in projects:
        areas = _classify_project_areas(p)
        year = None
        if p.end_date:
            year = p.end_date.year
        elif p.start_date:
            year = p.start_date.year
        for area in areas:
            _register(area, recency_year=year, depth_years=None)

    # Experiences
    for e in experiences:
        areas = _classify_experience_areas(e)
        year = None
        if e.end_date:
            year = e.end_date.year
        elif e.start_date:
            year = e.start_date.year if e.is_current else None
            if e.is_current:
                year = _now_utc().year
        exp_years = _experience_years(e)
        for area in areas:
            _register(area, recency_year=year, depth_years=exp_years if exp_years > 0 else None)

    # 2. fullstack collapse: if frontend+backend both have signal, add a
    # synthetic 'fullstack' bucket combining them (breadth = min, year = max).
    if FRONT_BACK_PAIR.issubset(per_area.keys()):
        f = per_area["frontend"]
        b = per_area["backend"]
        ratio = min(f["breadth"], b["breadth"]) / max(f["breadth"], b["breadth"])
        if ratio >= 0.5:
            per_area["fullstack"] = {
                "breadth": min(f["breadth"], b["breadth"]),
                "max_year": max(
                    [y for y in (f["max_year"], b["max_year"]) if y is not None],
                    default=None,
                ),
                "max_depth_years": max(f["max_depth_years"], b["max_depth_years"]),
            }

    # 3. Build AreaStrength rows
    now = _now_utc()
    strengths: list[AreaStrength] = []
    score_table: dict[str, float] = {}
    for area, slot in per_area.items():
        recency_months = _months_since(slot["max_year"])
        confidence = _confidence(slot["breadth"], recency_months)
        if confidence <= 0:
            continue
        strengths.append(
            AreaStrength(
                id=uuid4(),
                user_id=user_id,
                area=area,
                depth_years=float(slot["max_depth_years"]),
                breadth_count=int(slot["breadth"]),
                recency_months=recency_months,
                confidence=confidence,
                is_primary=False,
                computed_at=now,
            )
        )
        score_table[area] = confidence

    # 4. Decide is_primary: top 1-2 areas with confidence >= 0.55 AND within 0.7×top
    ranked = sorted(strengths, key=lambda s: s.confidence, reverse=True)
    primary_areas: list[str] = []
    if ranked:
        top_conf = ranked[0].confidence
        for s in ranked[:3]:
            if s.confidence >= 0.55 and s.confidence >= 0.7 * top_conf:
                s.is_primary = True
                primary_areas.append(s.area)
            if len(primary_areas) >= 2 and s is not ranked[0]:
                break
    secondary_areas = [s.area for s in ranked if s.area not in primary_areas][:4]

    shape_type = _infer_shape(score_table, primary_areas)

    # 5. Persist: upsert each strength + delete areas no longer present.
    repo = SqlAlchemyAreaStrengthRepository(session)
    existing_rows = await repo.list(user_id)
    existing_areas = {r.area for r in existing_rows}
    new_areas = {s.area for s in strengths}
    to_delete = list(existing_areas - new_areas)
    if to_delete:
        await repo.delete_areas(user_id, to_delete)
    for strength in strengths:
        # preserve id for existing area rows for idempotency in computed_at
        for existing in existing_rows:
            if existing.area == strength.area:
                strength.id = existing.id
                break
        await repo.upsert(strength)

    # 6. Update cached projection on universes
    await update_universe_areas(
        session,
        user_id=user_id,
        primary_area=primary_areas[0] if primary_areas else None,
        secondary_areas=secondary_areas,
    )

    return ShapeResult(
        user_id=user_id,
        strengths=strengths,
        primary_areas=primary_areas,
        secondary_areas=secondary_areas,
        shape_type=shape_type,
        computed_at=now,
    )


async def classify_entities_by_area(
    session: AsyncSession, user_id: UUID
) -> dict[str, str]:
    """Map each skill/project/experience to its single primary area.

    Reuses the same text blobs as `compute_area_strengths`, but resolves
    one cluster membership per entity (argmax) instead of aggregating.
    The graph snapshot uses this to colour and group nodes by coherent
    area (backend / frontend / cloud / ai_ml / …). Returns
    ``{str(entity_id): area}`` for entities that match at least one area.
    """
    skills, projects, experiences = await _load_universe_blob(session, user_id)
    out: dict[str, str] = {}

    for s in skills:
        area = primary_area(collect_text_blob([s.name, s.category]))
        if area:
            out[str(s.id)] = area

    for p in projects:
        stack = " ".join(str(x) for x in (p.tech_stack or []))
        area = primary_area(collect_text_blob([p.name, p.description, stack]))
        if area:
            out[str(p.id)] = area

    for e in experiences:
        comp = " ".join(str(c) for c in (e.competences or []))
        hl = " ".join(str(h) for h in (e.highlights or []))
        area = primary_area(collect_text_blob([e.role, e.description, comp, hl]))
        if area:
            out[str(e.id)] = area

    return out


async def load_area_strengths(
    session: AsyncSession, user_id: UUID
) -> tuple[list[AreaStrength], str | None, list[str]]:
    """Read cached shape from area_strengths + universes."""
    repo = SqlAlchemyAreaStrengthRepository(session)
    strengths = await repo.list(user_id)
    uni = await session.get(UniverseOrm, user_id)
    primary = uni.primary_area if uni else None
    secondary = list(uni.secondary_areas) if uni else []
    return strengths, primary, secondary


# Convenience: a lightweight wrapper for detect_software_area legacy callers.


def primary_area_from_strengths(strengths: list[AreaStrength]) -> tuple[str, float, str | None]:
    """Return (primary, confidence, secondary) tuple for back-compat."""
    if not strengths:
        return ("none", 0.0, None)
    ranked = sorted(strengths, key=lambda s: s.confidence, reverse=True)
    primary = ranked[0]
    secondary = ranked[1].area if len(ranked) > 1 else None
    return (primary.area, primary.confidence, secondary)


# Re-export for legacy modules that imported SOFTWARE_AREA_KEYWORDS from
# `src.agents.tools.insights_tools` historically.
__all__ = [
    "ShapeResult",
    "SOFTWARE_AREA_KEYWORDS",
    "compute_area_strengths",
    "load_area_strengths",
    "primary_area_from_strengths",
]
