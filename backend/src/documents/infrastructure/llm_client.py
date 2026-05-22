"""LLM client implementations.

`MockLlmClient` synthesizes a JSON Resume v1.0.0 document by:
  1. fetching the user's universe entities corresponding to the retrieved ids
  2. assembling them into JSON Resume sections
  3. lightly biasing bullet order toward keywords matched in the JD

It produces *real* CV content (not fake) — just without LLM rewriting.
Switching to the real Anthropic/OpenAI client is a class swap.
"""
from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.documents.application.ports import LlmClient
from src.identity.infrastructure.orm import UserOrm
from src.universe.infrastructure.orm import (
    EducationOrm,
    ExperienceOrm,
    LanguageOrm,
    ProjectOrm,
    SkillOrm,
    UniverseOrm,
)


class MockLlmClient(LlmClient):
    """Composes JSON Resume from actual universe entities."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def generate_cv_bullets(
        self,
        *,
        job_summary: dict[str, Any],
        retrieved: list[dict[str, Any]],
        language: str,
        tone: str | None,
    ) -> dict[str, Any]:
        # We don't actually use `retrieved` to fetch ids; instead we pull all
        # entities for the user via the RLS-scoped session.
        # `retrieved` is a hint we use to bias ordering.
        # We need the user_id; it's inferred from the session's RLS context.
        user_id = await self._current_user_id()
        if user_id is None:
            return _empty_resume(language)

        edu_rows = (
            await self._session.execute(
                select(EducationOrm)
                .where(EducationOrm.user_id == user_id)
                .where(EducationOrm.deleted_at.is_(None))
            )
        ).scalars().all()
        exp_rows = (
            await self._session.execute(
                select(ExperienceOrm)
                .where(ExperienceOrm.user_id == user_id)
                .where(ExperienceOrm.deleted_at.is_(None))
            )
        ).scalars().all()
        skill_rows = (
            await self._session.execute(
                select(SkillOrm)
                .where(SkillOrm.user_id == user_id)
                .where(SkillOrm.deleted_at.is_(None))
            )
        ).scalars().all()
        lang_rows = (
            await self._session.execute(
                select(LanguageOrm).where(LanguageOrm.user_id == user_id)
            )
        ).scalars().all()
        proj_rows = (
            await self._session.execute(
                select(ProjectOrm)
                .where(ProjectOrm.user_id == user_id)
                .where(ProjectOrm.deleted_at.is_(None))
            )
        ).scalars().all()
        universe = await self._session.get(UniverseOrm, user_id)
        user = await self._session.get(UserOrm, user_id)

        ats_keywords = set(job_summary.get("ats_keywords", []))

        def _bias(text: str) -> int:
            return sum(1 for k in ats_keywords if k.lower() in (text or "").lower())

        # Bias experience ordering by keyword density × recency
        sorted_exp = sorted(
            exp_rows,
            key=lambda e: (
                _bias((e.description or "") + " ".join(e.highlights or []) + " ".join(e.competences or [])),
                e.end_date or e.start_date or _DATE_MIN,
            ),
            reverse=True,
        )

        resume: dict[str, Any] = {
            "basics": {
                "name": (user.display_name if user else None) or (user.email if user else ""),
                "email": user.email if user else "",
                "label": universe.headline if universe else None,
                "summary": universe.summary if universe else None,
                "image": universe.photo_url if universe else None,
            },
            "work": [
                {
                    "name": e.organization,
                    "position": e.role,
                    "startDate": e.start_date.isoformat() if e.start_date else None,
                    "endDate": e.end_date.isoformat() if e.end_date else None,
                    "summary": e.description,
                    "highlights": e.highlights or [],
                    "url": e.url,
                }
                for e in sorted_exp
            ],
            "education": [
                {
                    "institution": ed.institution,
                    "area": ed.field_of_study,
                    "studyType": ed.degree,
                    "startDate": ed.start_date.isoformat() if ed.start_date else None,
                    "endDate": ed.end_date.isoformat() if ed.end_date else None,
                    "score": str(ed.gpa) if ed.gpa else None,
                    "url": ed.url,
                }
                for ed in edu_rows
            ],
            "skills": [
                {
                    "name": s.name,
                    "level": s.level or "",
                    "keywords": [],
                }
                for s in sorted(
                    skill_rows,
                    key=lambda s: (s.name.lower() in {k.lower() for k in ats_keywords}, s.years or 0),
                    reverse=True,
                )
            ],
            "languages": [
                {"language": lang.name, "fluency": lang.level}
                for lang in lang_rows
            ],
            "projects": [
                {
                    "name": p.name,
                    "description": p.description,
                    "highlights": p.highlights or [],
                    "keywords": p.tech_stack or [],
                    "url": p.url,
                    "startDate": p.start_date.isoformat() if p.start_date else None,
                    "endDate": p.end_date.isoformat() if p.end_date else None,
                }
                for p in proj_rows
            ],
            "meta": {
                "language": language,
                "tone": tone,
                "version": "v1.0.0",
                "canonical": "https://jsonresume.org/schema/",
                "generated_by": "cvs-saas MockLlmClient",
                "ats_target": job_summary.get("ats"),
                "ats_keywords_matched": sorted(ats_keywords)[:20],
            },
        }
        return resume

    async def generate_cover_letter(
        self,
        *,
        job_summary: dict[str, Any],
        retrieved: list[dict[str, Any]],
        language: str,
        tone: str | None,
    ) -> dict[str, Any]:
        """Compose a minimal cover-letter body from the user's top experiences
        and the JD title/company. Pure mock — no LLM call. Real LLM swap
        replaces this method only."""
        del retrieved  # bias hint not used yet
        user_id = await self._current_user_id()
        if user_id is None:
            return _empty_cover_letter(language)

        exp_rows = (
            await self._session.execute(
                select(ExperienceOrm)
                .where(ExperienceOrm.user_id == user_id)
                .where(ExperienceOrm.deleted_at.is_(None))
            )
        ).scalars().all()
        universe = await self._session.get(UniverseOrm, user_id)
        user = await self._session.get(UserOrm, user_id)

        name = (user.display_name if user else None) or (user.email if user else "")
        title = job_summary.get("title") or "el puesto"
        company = job_summary.get("company") or "su equipo"
        latest = sorted(
            exp_rows,
            key=lambda e: e.end_date or e.start_date or _DATE_MIN,
            reverse=True,
        )[:2]

        if language.lower().startswith("en"):
            greeting = f"Dear {company} team,"
            opener = f"I'm writing to apply for the {title} role."
            mid_parts = [
                f"In my most recent role at {e.organization} I worked as {e.role}." for e in latest
            ]
            close = "I'd love to talk about how my background fits this opportunity."
            sign = f"Best,\n{name}"
        else:
            greeting = f"Hola equipo de {company},"
            opener = f"Os escribo para postular a {title}."
            mid_parts = [
                f"En mi etapa más reciente en {e.organization} trabajé como {e.role}." for e in latest
            ]
            close = "Me encantaría hablar de cómo encajo en esta oportunidad."
            sign = f"Un saludo,\n{name}"

        body = "\n\n".join(
            [greeting, opener, *mid_parts, close, sign]
        )

        return {
            "basics": {
                "name": name,
                "email": user.email if user else "",
                "label": universe.headline if universe else None,
                "summary": body,
            },
            "cover_letter_body": body,
            "meta": {
                "language": language,
                "tone": tone,
                "version": "v1.0.0",
                "kind": "cover_letter",
                "target_company": company,
                "target_title": title,
            },
        }

    async def _current_user_id(self) -> UUID | None:
        from sqlalchemy import text

        try:
            row = (
                await self._session.execute(text("SELECT current_setting('app.current_user_id', true)"))
            ).first()
        except Exception:  # noqa: BLE001
            return None
        if row is None or not row[0]:
            return None
        try:
            return UUID(row[0])
        except (ValueError, TypeError):
            return None


from datetime import date as _date  # noqa: E402

_DATE_MIN = _date(1900, 1, 1)


def _empty_resume(language: str) -> dict[str, Any]:
    return {
        "basics": {},
        "work": [],
        "education": [],
        "skills": [],
        "languages": [],
        "projects": [],
        "meta": {"language": language, "version": "v1.0.0"},
    }


def _empty_cover_letter(language: str) -> dict[str, Any]:
    return {
        "basics": {"summary": ""},
        "cover_letter_body": "",
        "meta": {"language": language, "version": "v1.0.0", "kind": "cover_letter"},
    }
