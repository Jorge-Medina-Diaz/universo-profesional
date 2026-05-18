"""MCP tools registry — the 8 core tools per §I.4 of the spec.

Each tool delegates to the corresponding use case from the Universe / Documents
contexts, so the same logic powers both REST and MCP — no logic divergence.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Awaitable, Callable
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

ToolHandler = Callable[..., Awaitable[Any]]


@dataclass(frozen=True)
class ToolSpec:
    name: str
    description: str
    input_schema: dict[str, Any]
    handler: Any
    required_scope: str | None = None


# --- Helpers --------------------------------------------------------------


async def _uow(session: AsyncSession):  # type: ignore[no-untyped-def]
    from src.shared.uow import UnitOfWork

    return UnitOfWork(session)


def _session_only_deps(session: AsyncSession):  # type: ignore[no-untyped-def]
    """Shortcut: build all the same DI used by the REST router."""
    from src.shared.embeddings import get_embeddings_service
    from src.universe.infrastructure.repositories import (
        SqlAlchemyAchievementRepository,
        SqlAlchemyCareerPreferencesRepository,
        SqlAlchemyCertificationRepository,
        SqlAlchemyCourseRepository,
        SqlAlchemyEducationRepository,
        SqlAlchemyExperienceRepository,
        SqlAlchemyInterestRepository,
        SqlAlchemyLanguageRepository,
        SqlAlchemyProjectRepository,
        SqlAlchemySkillRepository,
        SqlAlchemyUniverseRepository,
    )
    from src.universe.infrastructure.scheduler import ArqEmbeddingScheduler
    from src.universe.infrastructure.semantic_search import PgVectorSemanticSearch

    scheduler = ArqEmbeddingScheduler()
    return {
        "scheduler": scheduler,
        "edu_repo": SqlAlchemyEducationRepository(session),
        "exp_repo": SqlAlchemyExperienceRepository(session),
        "proj_repo": SqlAlchemyProjectRepository(session),
        "skill_repo": SqlAlchemySkillRepository(session),
        "cert_repo": SqlAlchemyCertificationRepository(session),
        "course_repo": SqlAlchemyCourseRepository(session),
        "lang_repo": SqlAlchemyLanguageRepository(session),
        "ach_repo": SqlAlchemyAchievementRepository(session),
        "int_repo": SqlAlchemyInterestRepository(session),
        "prefs_repo": SqlAlchemyCareerPreferencesRepository(session),
        "univ_repo": SqlAlchemyUniverseRepository(session),
        "search": PgVectorSemanticSearch(session),
        "embedder": get_embeddings_service(),
    }


# --- get_profile ---------------------------------------------------------


async def _h_get_profile(
    *, session: AsyncSession, user_id: UUID, client_id: UUID, args: dict[str, Any]
) -> Any:
    from src.universe.application.use_cases import GetUniverseSummary

    deps = _session_only_deps(session)
    uc = GetUniverseSummary(
        deps["univ_repo"],
        deps["edu_repo"],
        deps["exp_repo"],
        deps["skill_repo"],
        deps["lang_repo"],
        deps["proj_repo"],
        deps["prefs_repo"],
    )
    section = args.get("section", "all")
    summary = await uc.execute(user_id=str(user_id))
    if section == "all":
        return summary
    # Return only that section
    if section == "education":
        return await deps["edu_repo"].list(user_id)
    if section == "experience":
        return await deps["exp_repo"].list(user_id)
    if section == "skill":
        return await deps["skill_repo"].list(user_id)
    return summary


# --- get_universe_summary ------------------------------------------------


async def _h_summary(
    *, session: AsyncSession, user_id: UUID, client_id: UUID, args: dict[str, Any]
) -> Any:
    return await _h_get_profile(session=session, user_id=user_id, client_id=client_id, args={})


# --- add_education -------------------------------------------------------


async def _h_add_education(
    *, session: AsyncSession, user_id: UUID, client_id: UUID, args: dict[str, Any]
) -> Any:
    from src.universe.application.use_cases import EducationCrud
    from src.shared.uow import UnitOfWork

    deps = _session_only_deps(session)
    uc = EducationCrud(deps["edu_repo"], deps["scheduler"])
    uow = UnitOfWork(session)
    r = await uc.add(user_id=str(user_id), payload=args, uow=uow)
    if r.is_failure:
        raise r.error  # type: ignore[union-attr]
    return r.value  # type: ignore[union-attr]


# --- update_education ---------------------------------------------------


async def _h_update_education(
    *, session: AsyncSession, user_id: UUID, client_id: UUID, args: dict[str, Any]
) -> Any:
    from src.universe.application.use_cases import EducationCrud
    from src.shared.uow import UnitOfWork

    deps = _session_only_deps(session)
    uc = EducationCrud(deps["edu_repo"], deps["scheduler"])
    uow = UnitOfWork(session)
    entity_id = args.pop("id", None)
    if not entity_id:
        raise ValueError("Missing id")
    r = await uc.update(user_id=str(user_id), entity_id=entity_id, patch=args, uow=uow)
    if r.is_failure:
        raise r.error  # type: ignore[union-attr]
    return r.value  # type: ignore[union-attr]


# --- add_experience ----------------------------------------------------


async def _h_add_experience(
    *, session: AsyncSession, user_id: UUID, client_id: UUID, args: dict[str, Any]
) -> Any:
    from src.universe.application.use_cases import ExperienceCrud
    from src.shared.uow import UnitOfWork

    deps = _session_only_deps(session)
    uc = ExperienceCrud(deps["exp_repo"], deps["scheduler"])
    uow = UnitOfWork(session)
    r = await uc.add(user_id=str(user_id), payload=args, uow=uow)
    if r.is_failure:
        raise r.error  # type: ignore[union-attr]
    return r.value  # type: ignore[union-attr]


# --- add_skill ----------------------------------------------------------


async def _h_add_skill(
    *, session: AsyncSession, user_id: UUID, client_id: UUID, args: dict[str, Any]
) -> Any:
    from src.universe.application.use_cases import SkillCrud
    from src.shared.uow import UnitOfWork

    deps = _session_only_deps(session)
    uc = SkillCrud(deps["skill_repo"], deps["scheduler"])
    uow = UnitOfWork(session)
    r = await uc.add(user_id=str(user_id), payload=args, uow=uow)
    if r.is_failure:
        raise r.error  # type: ignore[union-attr]
    return r.value  # type: ignore[union-attr]


# --- match_job_to_profile ----------------------------------------------


async def _h_match_job(
    *, session: AsyncSession, user_id: UUID, client_id: UUID, args: dict[str, Any]
) -> Any:
    from src.documents.infrastructure.job_parser import MockJobParser

    parser = MockJobParser()
    parsed = await parser.parse(
        url=args.get("job_url"), description=args.get("job_description")
    )
    deps = _session_only_deps(session)
    jd_text = parsed.get("description_raw") or " ".join(str(v) for v in parsed.values())
    vec = await deps["embedder"].embed(jd_text)
    retrieved = await deps["search"].search(user_id=user_id, embedding=vec, top_k=20)
    # Compute simple match score
    if retrieved:
        avg = sum(r["score"] for r in retrieved) / len(retrieved)
    else:
        avg = 0.0
    match_score = int(round(max(0.0, min(1.0, (avg + 1) / 2)) * 100))
    your_skills = {s.name.lower() for s in await deps["skill_repo"].list(user_id)}
    needed = {k.lower() for k in parsed.get("ats_keywords", [])}
    gaps = sorted(needed - your_skills)
    strengths = sorted(your_skills & needed)
    return {
        "match_score": match_score,
        "gaps": gaps,
        "strengths": strengths,
        "suggested_keywords": list(parsed.get("ats_keywords", []))[:15],
        "parsed_jd": parsed,
        "retrieved": retrieved[:10],
    }


# --- generate_cv -------------------------------------------------------


async def _h_generate_cv(
    *, session: AsyncSession, user_id: UUID, client_id: UUID, args: dict[str, Any]
) -> Any:
    from src.billing.application.use_cases import CheckQuota
    from src.billing.infrastructure.repositories import (
        SqlAlchemyQuotaRepository,
        SqlAlchemySubscriptionRepository,
    )
    from src.documents.application.use_cases import GenerateCv, GenerateCvInput
    from src.documents.infrastructure.job_parser import MockJobParser
    from src.documents.infrastructure.llm_client import MockLlmClient
    from src.documents.infrastructure.renderer import WeasyPrintRenderer
    from src.documents.infrastructure.repositories import (
        SqlAlchemyDocumentRepository,
        SqlAlchemyJobRepository,
    )
    from src.shared.embeddings import get_embeddings_service
    from src.shared.uow import UnitOfWork
    from src.universe.infrastructure.semantic_search import PgVectorSemanticSearch

    # MCP access requires Premium+ — enforced via billing quota
    quota = CheckQuota(
        SqlAlchemySubscriptionRepository(session),
        SqlAlchemyQuotaRepository(session),
    )
    qr = await quota.execute(user_id=str(user_id), resource="mcp_call")
    if qr.is_failure:
        raise qr.error  # type: ignore[union-attr]
    await quota.increment(user_id=str(user_id), resource="mcp_call")

    qr2 = await quota.execute(user_id=str(user_id), resource="cv_generated")
    if qr2.is_failure:
        raise qr2.error  # type: ignore[union-attr]

    uc = GenerateCv(
        documents=SqlAlchemyDocumentRepository(session),
        jobs=SqlAlchemyJobRepository(session),
        parser=MockJobParser(),
        embedder=get_embeddings_service(),
        search=PgVectorSemanticSearch(session),
        llm=MockLlmClient(session),
        renderer=WeasyPrintRenderer(),
    )
    uow = UnitOfWork(session)
    r = await uc.execute(
        user_id=str(user_id),
        payload=GenerateCvInput(
            job_url=args.get("job_url"),
            job_description=args.get("job_description"),
            template=args.get("template", "ats-classic"),
            language=args.get("language", "es"),
            tone=args.get("tone", "professional"),
            length=args.get("length", "1-page"),
        ),
        uow=uow,
    )
    if r.is_failure:
        raise r.error  # type: ignore[union-attr]
    await quota.increment(user_id=str(user_id), resource="cv_generated")
    dto = r.value  # type: ignore[union-attr]
    return {
        "document_id": dto.document_id,
        "pdf_url": dto.pdf_url,
        "docx_url": dto.docx_url,
        "json_resume": dto.json_resume,
    }


# --- Registry ----------------------------------------------------------


TOOLS: dict[str, ToolSpec] = {
    "get_profile": ToolSpec(
        name="get_profile",
        description="Get a section (or all) of the authenticated user's professional universe.",
        input_schema={
            "type": "object",
            "properties": {
                "section": {
                    "type": "string",
                    "enum": ["all", "education", "experience", "skill"],
                    "default": "all",
                }
            },
        },
        handler=_h_get_profile,
        required_scope="universe:read",
    ),
    "get_universe_summary": ToolSpec(
        name="get_universe_summary",
        description="Compact summary: headline, counts, top skills, recent experiences, languages.",
        input_schema={"type": "object", "properties": {}},
        handler=_h_summary,
        required_scope="universe:read",
    ),
    "add_education": ToolSpec(
        name="add_education",
        description="Add an education entry to the user's universe.",
        input_schema={
            "type": "object",
            "required": ["institution"],
            "properties": {
                "institution": {"type": "string"},
                "degree": {"type": "string"},
                "field_of_study": {"type": "string"},
                "start_date": {"type": "string", "format": "date"},
                "end_date": {"type": "string", "format": "date"},
                "is_current": {"type": "boolean"},
                "description": {"type": "string"},
                "highlights": {"type": "array", "items": {"type": "string"}},
                "gpa": {"type": "number"},
                "url": {"type": "string"},
            },
        },
        handler=_h_add_education,
        required_scope="universe:write",
    ),
    "update_education": ToolSpec(
        name="update_education",
        description="Patch an existing education entry by id.",
        input_schema={
            "type": "object",
            "required": ["id"],
            "properties": {"id": {"type": "string", "format": "uuid"}},
            "additionalProperties": True,
        },
        handler=_h_update_education,
        required_scope="universe:write",
    ),
    "add_experience": ToolSpec(
        name="add_experience",
        description="Add a work experience entry.",
        input_schema={
            "type": "object",
            "required": ["organization", "role"],
            "properties": {
                "organization": {"type": "string"},
                "role": {"type": "string"},
                "start_date": {"type": "string", "format": "date"},
                "end_date": {"type": "string", "format": "date"},
                "is_current": {"type": "boolean"},
                "modality": {"type": "string", "enum": ["remote", "hybrid", "onsite"]},
                "description": {"type": "string"},
                "highlights": {"type": "array", "items": {"type": "string"}},
                "competences": {"type": "array", "items": {"type": "string"}},
            },
        },
        handler=_h_add_experience,
        required_scope="universe:write",
    ),
    "add_skill": ToolSpec(
        name="add_skill",
        description="Add a skill with category and level.",
        input_schema={
            "type": "object",
            "required": ["name"],
            "properties": {
                "name": {"type": "string"},
                "category": {"type": "string", "enum": ["hard", "soft", "tool", "methodology"]},
                "level": {"type": "string", "enum": ["basic", "intermediate", "high", "expert"]},
                "years": {"type": "integer"},
                "evidence_refs": {"type": "array", "items": {"type": "string"}},
            },
        },
        handler=_h_add_skill,
        required_scope="universe:write",
    ),
    "match_job_to_profile": ToolSpec(
        name="match_job_to_profile",
        description="Score a job description (URL or text) against the user's universe.",
        input_schema={
            "type": "object",
            "properties": {
                "job_url": {"type": "string"},
                "job_description": {"type": "string"},
            },
        },
        handler=_h_match_job,
        required_scope="universe:read",
    ),
    "generate_cv": ToolSpec(
        name="generate_cv",
        description="Generate an ATS-adapted CV (PDF + DOCX + JSON Resume) for a job.",
        input_schema={
            "type": "object",
            "properties": {
                "job_url": {"type": "string"},
                "job_description": {"type": "string"},
                "template": {"type": "string", "default": "ats-classic"},
                "language": {"type": "string", "enum": ["es", "en"], "default": "es"},
                "tone": {"type": "string", "default": "professional"},
                "length": {"type": "string", "enum": ["1-page", "2-page"], "default": "1-page"},
            },
        },
        handler=_h_generate_cv,
        required_scope="documents:generate",
    ),
}
