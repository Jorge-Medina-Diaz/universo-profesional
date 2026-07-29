"""LLM client implementations.

`MockLlmClient` synthesizes a JSON Resume v1.0.0 document by:
  1. fetching the user's universe entities corresponding to the retrieved ids
  2. assembling them into JSON Resume sections
  3. lightly biasing bullet order toward keywords matched in the JD

It produces *real* CV content (not fake) — just without LLM rewriting.

`AiLlmClient` builds on that grounded base: it reuses the same composition
(so the *structure* always comes from the user's real entities and nothing
is fabricated), then runs a single LLM pass that only **rephrases** the
prose fields — the professional summary and each work entry's bullets —
to the target job. The model can never add a job/skill/degree the user
doesn't have, because tailored prose is merged field-by-field back onto
the grounded structure by index. On any LLM failure it degrades to the
grounded base.
"""
from __future__ import annotations

from typing import Any
from uuid import UUID

import structlog
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.documents.application.ports import LlmClient
from src.identity.infrastructure.orm import UserOrm
from src.shared.config import get_settings
from src.shared.llm_client import get_llm_client
from src.universe.infrastructure.orm import (
    EducationOrm,
    ExperienceOrm,
    LanguageOrm,
    ProjectOrm,
    SkillOrm,
    UniverseOrm,
)

logger = structlog.get_logger(__name__)


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
        except Exception:
            return None
        if row is None or not row[0]:
            return None
        try:
            return UUID(row[0])
        except (ValueError, TypeError):
            return None


class _TailoredWorkEntry(BaseModel):
    index: int = Field(description="0-based index of the work entry being rewritten.")
    summary: str | None = Field(
        default=None,
        description="One-sentence role summary, rephrased to emphasise what the job cares about. Optional.",
    )
    highlights: list[str] = Field(
        default_factory=list,
        description="3-5 achievement bullets, each starting with an action verb and grounded ONLY in facts present in the provided entry. Do not invent metrics or responsibilities.",
    )


class _TailoredCv(BaseModel):
    summary: str = Field(
        description="A 2-4 sentence professional summary tailored to the job. Use ONLY facts present in the candidate profile (skills, roles, projects). Never invent experience the candidate lacks.",
    )
    work: list[_TailoredWorkEntry] = Field(
        default_factory=list,
        description="Rephrased prose for each work entry, referenced by its 0-based index. Omit entries you don't change.",
    )


class _TailoredCoverLetter(BaseModel):
    body: str = Field(
        description="A complete, professional cover-letter body in the requested language. Ground every claim in the provided profile facts — do not invent employers, titles, or skills the candidate doesn't have.",
    )


def _facts_for_prompt(resume: dict[str, Any]) -> str:
    """Compact, LLM-friendly rendering of the grounded resume facts."""
    import json

    basics = resume.get("basics") or {}
    payload = {
        "name": basics.get("name"),
        "current_headline": basics.get("label"),
        "current_summary": basics.get("summary"),
        "skills": [s.get("name") for s in (resume.get("skills") or [])],
        "languages": [
            f"{lang.get('language')} ({lang.get('fluency')})"
            for lang in (resume.get("languages") or [])
        ],
        "work": [
            {
                "index": i,
                "organization": w.get("name"),
                "position": w.get("position"),
                "summary": w.get("summary"),
                "highlights": w.get("highlights") or [],
            }
            for i, w in enumerate(resume.get("work") or [])
        ],
        "projects": [
            {"name": p.get("name"), "description": p.get("description"), "tech": p.get("keywords")}
            for p in (resume.get("projects") or [])
        ],
        "education": [
            {"institution": e.get("institution"), "study": e.get("studyType"), "area": e.get("area")}
            for e in (resume.get("education") or [])
        ],
    }
    return json.dumps(payload, ensure_ascii=False, indent=2)


def _job_for_prompt(job_summary: dict[str, Any]) -> str:
    import json

    return json.dumps(
        {
            "title": job_summary.get("title"),
            "company": job_summary.get("company"),
            "must_haves": job_summary.get("must_haves"),
            "nice_to_haves": job_summary.get("nice_to_haves"),
            "keywords": job_summary.get("ats_keywords"),
            "description": (job_summary.get("description_raw") or "")[:4000],
        },
        ensure_ascii=False,
        indent=2,
    )


class AiLlmClient(LlmClient):
    """Grounded-tailoring client: real entities for structure, LLM for prose."""

    def __init__(self, session: AsyncSession, user_id: UUID | None = None) -> None:
        self._session = session
        self._user_id = user_id
        self._grounded = MockLlmClient(session)
        self._llm = get_llm_client()

    async def _log_usage(self, provider: str, model: str) -> None:
        """Persist usage from the last LLM call if metadata is available."""
        if not self._user_id:
            return
        usage = getattr(self._llm, "last_usage", None)
        if not usage:
            return
        from src.llm_tracking.application.tracker import log_document_llm_call
        from src.llm_tracking.infrastructure.repository import SqlalchemyLlmUsageLogRepository

        await log_document_llm_call(
            SqlalchemyLlmUsageLogRepository(self._session),
            user_id=self._user_id,
            provider=provider,
            model=model,
            input_tokens=usage.get("input_tokens", 0),
            output_tokens=usage.get("output_tokens", 0),
            cache_read_tokens=usage.get("cache_read_tokens", 0),
            cache_write_tokens=usage.get("cache_write_tokens", 0),
        )

    async def generate_cv_bullets(
        self,
        *,
        job_summary: dict[str, Any],
        retrieved: list[dict[str, Any]],
        language: str,
        tone: str | None,
    ) -> dict[str, Any]:
        resume = await self._grounded.generate_cv_bullets(
            job_summary=job_summary, retrieved=retrieved, language=language, tone=tone
        )
        # Nothing to tailor for an empty profile.
        if not (resume.get("skills") or resume.get("work") or resume.get("projects")):
            return resume
        system = (
            "You are an expert CV writer. You tailor an existing, factual professional "
            "profile to a specific job posting. You MUST NOT invent experience, employers, "
            "titles, metrics, or skills that are not present in the profile facts. You only "
            f"rephrase and re-emphasise what is already there. Write in language '{language}' "
            f"with a {tone or 'professional'} tone."
        )
        prompt = (
            "## Candidate profile (facts — do not contradict or extend)\n"
            f"{_facts_for_prompt(resume)}\n\n"
            "## Target job\n"
            f"{_job_for_prompt(job_summary)}\n\n"
            "Produce a tailored professional summary and, for each work entry, rephrased "
            "highlights that surface the most job-relevant evidence. Reference work entries "
            "by their 0-based index. Ground everything in the facts above."
        )
        try:
            tailored = await self._llm.structured(
                system=system, prompt=prompt, schema=_TailoredCv, max_tokens=2048, temperature=0.4
            )
            await self._log_usage(get_settings().llm_provider_resolved, getattr(self._llm, "_model", "unknown"))
        except Exception as exc:
            logger.warning("cv_tailoring_failed_using_grounded", error=str(exc))
            return resume

        if tailored.summary.strip():
            resume.setdefault("basics", {})["summary"] = tailored.summary.strip()
        work = resume.get("work") or []
        for entry in tailored.work:
            if 0 <= entry.index < len(work):
                if entry.summary and entry.summary.strip():
                    work[entry.index]["summary"] = entry.summary.strip()
                if entry.highlights:
                    work[entry.index]["highlights"] = [h for h in entry.highlights if h.strip()]
        meta = resume.setdefault("meta", {})
        meta["generated_by"] = f"cvs-saas AiLlmClient/{get_settings().llm_provider_resolved}"
        return resume

    async def generate_cover_letter(
        self,
        *,
        job_summary: dict[str, Any],
        retrieved: list[dict[str, Any]],
        language: str,
        tone: str | None,
    ) -> dict[str, Any]:
        base = await self._grounded.generate_cover_letter(
            job_summary=job_summary, retrieved=retrieved, language=language, tone=tone
        )
        facts = await self._grounded.generate_cv_bullets(
            job_summary=job_summary, retrieved=retrieved, language=language, tone=tone
        )
        if not (facts.get("skills") or facts.get("work") or facts.get("projects")):
            return base
        company = job_summary.get("company") or ""
        title = job_summary.get("title") or ""
        system = (
            "You are an expert cover-letter writer. Ground every claim in the candidate's "
            "factual profile — never invent employers, titles, metrics, or skills they lack. "
            f"Write the letter body in language '{language}' with a {tone or 'professional'} tone. "
            "Return only the letter body (greeting through sign-off), no preamble."
        )
        prompt = (
            "## Candidate profile (facts)\n"
            f"{_facts_for_prompt(facts)}\n\n"
            "## Target job\n"
            f"{_job_for_prompt(job_summary)}\n\n"
            f"Write a concise, compelling cover letter for the {title or 'role'} at "
            f"{company or 'the company'}. 3-4 short paragraphs."
        )
        try:
            tailored = await self._llm.structured(
                system=system,
                prompt=prompt,
                schema=_TailoredCoverLetter,
                max_tokens=1500,
                temperature=0.5,
            )
            await self._log_usage(get_settings().llm_provider_resolved, getattr(self._llm, "_model", "unknown"))
        except Exception as exc:
            logger.warning("cover_letter_tailoring_failed_using_grounded", error=str(exc))
            return base

        body = tailored.body.strip()
        if not body:
            return base
        base.setdefault("basics", {})["summary"] = body
        base["cover_letter_body"] = body
        base.setdefault("meta", {})["generated_by"] = (
            f"cvs-saas AiLlmClient/{get_settings().llm_provider_resolved}"
        )
        return base


def build_document_llm_client(session: AsyncSession, user_id: UUID | None = None) -> LlmClient:
    """Pick the real grounded-tailoring client when a provider is configured,
    else the deterministic mock. Mirrors the provider-resolution pattern used
    across the codebase (a single key auto-activates real generation)."""
    settings = get_settings()
    if settings.llm_provider_resolved == "mock":
        # Never generate a real user's CV from the fabricating mock client where
        # mock isn't allowed (prod without a key).
        settings.assert_llm_usable()
        return MockLlmClient(session)
    return AiLlmClient(session, user_id=user_id)


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
