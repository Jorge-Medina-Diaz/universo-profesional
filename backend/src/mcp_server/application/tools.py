"""MCP tools registry — Sprint 2 expansion to ~35 tools covering the full lifecycle.

Categories:
  * Universe write (add/update/delete) for each of the 9 entities + preferences + header
  * Universe read (get_profile, get_universe_summary, list_skills, search)
  * Integrations (connect/sync/disconnect + import linkedin/pdf)
  * Suggestions + Reminders + Activity
  * Documents (list, get, share, generate_cv)
  * Evidence + Avatar + Mark reviewed

Each tool delegates to the same use cases used by REST routes — no duplicate logic.
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


# --- Universe deps (build once per call) ------------------------------------


def _session_only_deps(session: AsyncSession):  # type: ignore[no-untyped-def]
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


def _new_uow(session: AsyncSession):  # type: ignore[no-untyped-def]
    from src.shared.uow import UnitOfWork

    return UnitOfWork(session)


# --- Universe read ----------------------------------------------------------


async def _h_get_profile(*, session, user_id, client_id, args):
    from src.universe.application.use_cases import GetUniverseSummary

    deps = _session_only_deps(session)
    uc = GetUniverseSummary(
        deps["univ_repo"], deps["edu_repo"], deps["exp_repo"], deps["skill_repo"],
        deps["lang_repo"], deps["proj_repo"], deps["prefs_repo"],
    )
    section = args.get("section", "all")
    summary = await uc.execute(user_id=str(user_id))
    if section == "all":
        return summary
    if section == "education":
        return await deps["edu_repo"].list(user_id)
    if section == "experience":
        return await deps["exp_repo"].list(user_id)
    if section == "skill":
        return await deps["skill_repo"].list(user_id)
    return summary


async def _h_summary(*, session, user_id, client_id, args):
    return await _h_get_profile(session=session, user_id=user_id, client_id=client_id, args={})


async def _h_list_skills(*, session, user_id, client_id, args):
    deps = _session_only_deps(session)
    skills = await deps["skill_repo"].list(user_id)
    category = args.get("category")
    min_level = args.get("min_level")
    min_years = args.get("min_years")
    level_rank = {"basic": 1, "intermediate": 2, "high": 3, "expert": 4}
    out = []
    for s in skills:
        if category and s.category != category:
            continue
        if min_level and level_rank.get(s.level or "", 0) < level_rank.get(min_level, 0):
            continue
        if min_years and (s.years or 0) < min_years:
            continue
        out.append({"id": str(s.id), "name": s.name, "category": s.category, "level": s.level, "years": s.years})
    return out


async def _h_search(*, session, user_id, client_id, args):
    from src.universe.application.use_cases import SearchUniverse

    deps = _session_only_deps(session)
    uc = SearchUniverse(deps["search"], deps["embedder"])
    return await uc.execute(
        user_id=str(user_id),
        query=args["query"],
        top_k=int(args.get("top_k") or 10),
        entity_types=args.get("entity_types"),
    )


# --- Universe write (CRUD per entity, via factories) ------------------------

_CRUD_CLASSES = {
    "education": "EducationCrud",
    "experience": "ExperienceCrud",
    "project": "ProjectCrud",
    "skill": "SkillCrud",
    "certification": "CertificationCrud",
    "course": "CourseCrud",
    "language": "LanguageCrud",
    "achievement": "AchievementCrud",
    "interest": "InterestCrud",
}

_REPO_KEYS = {
    "education": "edu_repo",
    "experience": "exp_repo",
    "project": "proj_repo",
    "skill": "skill_repo",
    "certification": "cert_repo",
    "course": "course_repo",
    "language": "lang_repo",
    "achievement": "ach_repo",
    "interest": "int_repo",
}


def _build_crud(session, entity: str):  # type: ignore[no-untyped-def]
    from src.universe.application import use_cases as uc

    deps = _session_only_deps(session)
    cls = getattr(uc, _CRUD_CLASSES[entity])
    repo = deps[_REPO_KEYS[entity]]
    return cls(repo, deps["scheduler"])


def _make_add_handler(entity: str):
    async def handler(*, session, user_id, client_id, args):
        uc_inst = _build_crud(session, entity)
        uow = _new_uow(session)
        r = await uc_inst.add(user_id=str(user_id), payload=dict(args), uow=uow)
        if r.is_failure:
            raise r.error  # type: ignore[union-attr]
        return r.value

    return handler


def _make_update_handler(entity: str):
    async def handler(*, session, user_id, client_id, args):
        uc_inst = _build_crud(session, entity)
        uow = _new_uow(session)
        args = dict(args)
        entity_id = args.pop("id", None)
        if not entity_id:
            raise ValueError("Missing id")
        r = await uc_inst.update(
            user_id=str(user_id), entity_id=entity_id, patch=args, uow=uow
        )
        if r.is_failure:
            raise r.error  # type: ignore[union-attr]
        return r.value

    return handler


def _make_delete_handler(entity: str):
    async def handler(*, session, user_id, client_id, args):
        uc_inst = _build_crud(session, entity)
        uow = _new_uow(session)
        r = await uc_inst.delete(user_id=str(user_id), entity_id=args["id"], uow=uow)
        if r.is_failure:
            raise r.error  # type: ignore[union-attr]
        return {"deleted": True}

    return handler


# --- Preferences + header ---------------------------------------------------


async def _h_set_prefs(*, session, user_id, client_id, args):
    from src.universe.application.use_cases import SetCareerPreferences

    deps = _session_only_deps(session)
    return await SetCareerPreferences(deps["prefs_repo"]).execute(
        user_id=str(user_id), patch=dict(args)
    )


async def _h_get_prefs(*, session, user_id, client_id, args):
    from src.universe.application.use_cases import GetCareerPreferences

    deps = _session_only_deps(session)
    return await GetCareerPreferences(deps["prefs_repo"]).execute(user_id=str(user_id))


async def _h_update_header(*, session, user_id, client_id, args):
    from src.universe.application.use_cases import UpdateUniverseHeader

    deps = _session_only_deps(session)
    uc = UpdateUniverseHeader(deps["univ_repo"])
    uow = _new_uow(session)
    return await uc.execute(user_id=str(user_id), patch=dict(args), uow=uow)


# --- Mark reviewed + Evidence + Activity -----------------------------------


async def _h_mark_reviewed(*, session, user_id, client_id, args):
    from src.universe.application.use_cases import MarkReviewed

    r = await MarkReviewed(session).execute(
        user_id=str(user_id),
        entity_type=args["entity_type"],
        entity_id=args["entity_id"],
    )
    if r.is_failure:
        raise r.error  # type: ignore[union-attr]
    return r.value


async def _h_link_evidence(*, session, user_id, client_id, args):
    from src.universe.application.use_cases import LinkEvidence

    r = await LinkEvidence(session).execute(
        user_id=str(user_id),
        skill_id=args["skill_id"],
        evidence_entity_type=args["evidence_entity_type"],
        evidence_entity_id=args["evidence_entity_id"],
        weight=float(args.get("weight", 1.0)),
        notes=args.get("notes"),
    )
    if r.is_failure:
        raise r.error  # type: ignore[union-attr]
    return r.value


async def _h_get_activity(*, session, user_id, client_id, args):
    from src.universe.application.use_cases import GetActivity

    return await GetActivity(session).execute(
        user_id=str(user_id),
        limit=int(args.get("limit") or 50),
        since=args.get("since"),
        event_types=args.get("event_types"),
    )


# --- Match job + Generate CV ------------------------------------------------


async def _h_match_job(*, session, user_id, client_id, args):
    from src.documents.infrastructure.job_parser import MockJobParser

    parser = MockJobParser()
    parsed = await parser.parse(url=args.get("job_url"), description=args.get("job_description"))
    deps = _session_only_deps(session)
    jd_text = parsed.get("description_raw") or " ".join(str(v) for v in parsed.values())
    vec = await deps["embedder"].embed(jd_text)
    retrieved = await deps["search"].search(user_id=user_id, embedding=vec, top_k=20)
    avg = sum(r["score"] for r in retrieved) / len(retrieved) if retrieved else 0.0
    match_score = int(round(max(0.0, min(1.0, (avg + 1) / 2)) * 100))
    your_skills = {s.name.lower() for s in await deps["skill_repo"].list(user_id)}
    needed = {k.lower() for k in parsed.get("ats_keywords", [])}
    return {
        "match_score": match_score,
        "gaps": sorted(needed - your_skills),
        "strengths": sorted(your_skills & needed),
        "suggested_keywords": list(parsed.get("ats_keywords", []))[:15],
        "parsed_jd": parsed,
        "retrieved": retrieved[:10],
    }


async def _h_generate_cv(*, session, user_id, client_id, args):
    from src.billing.application.use_cases import CheckQuota
    from src.billing.infrastructure.repositories import (
        SqlAlchemyQuotaRepository,
        SqlAlchemySubscriptionRepository,
    )
    from src.documents.application.use_cases import GenerateCv, GenerateCvInput
    from src.documents.infrastructure.job_parser import MockJobParser
    from src.documents.infrastructure.llm_client import build_document_llm_client
    from src.documents.infrastructure.renderer import WeasyPrintRenderer
    from src.documents.infrastructure.repositories import (
        SqlAlchemyDocumentRepository,
        SqlAlchemyJobRepository,
    )
    from src.shared.embeddings import get_embeddings_service
    from src.universe.infrastructure.semantic_search import PgVectorSemanticSearch

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
        llm=build_document_llm_client(session),
        renderer=WeasyPrintRenderer(),
    )
    uow = _new_uow(session)
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


# --- Documents read ---------------------------------------------------------


async def _h_list_documents(*, session, user_id, client_id, args):
    from src.documents.application.use_cases import ListDocuments
    from src.documents.infrastructure.repositories import SqlAlchemyDocumentRepository

    return await ListDocuments(SqlAlchemyDocumentRepository(session)).execute(
        user_id=str(user_id), kind=args.get("kind"), limit=int(args.get("limit") or 20)
    )


async def _h_get_document(*, session, user_id, client_id, args):
    from src.documents.application.use_cases import GetDocument
    from src.documents.infrastructure.repositories import SqlAlchemyDocumentRepository

    r = await GetDocument(SqlAlchemyDocumentRepository(session)).execute(
        user_id=str(user_id), document_id=args["id"]
    )
    if r.is_failure:
        raise r.error  # type: ignore[union-attr]
    return r.value


async def _h_share_document(*, session, user_id, client_id, args):
    from src.documents.application.use_cases import ShareDocument
    from src.documents.infrastructure.repositories import SqlAlchemyDocumentRepository

    r = await ShareDocument(SqlAlchemyDocumentRepository(session)).execute(
        user_id=str(user_id),
        document_id=args["id"],
        expires_in_days=int(args.get("expires_in_days") or 30),
    )
    if r.is_failure:
        raise r.error  # type: ignore[union-attr]
    return r.value


# --- Integrations -----------------------------------------------------------


async def _h_list_connections(*, session, user_id, client_id, args):
    from src.integrations.application.connect_disconnect import ListConnections
    from src.integrations.infrastructure.repositories import SqlExternalAccountRepository

    return await ListConnections(SqlExternalAccountRepository(session)).execute(
        user_id=str(user_id)
    )


async def _h_sync_github(*, session, user_id, client_id, args):
    from src.integrations.application.github_sync import SyncGithub
    from src.integrations.infrastructure.repositories import (
        SqlExternalAccountRepository,
        SqlSyncRunsRepository,
    )
    from src.universe.infrastructure.repositories import (
        SqlAlchemyExperienceRepository,
        SqlAlchemyInterestRepository,
        SqlAlchemyProjectRepository,
        SqlAlchemySkillRepository,
    )

    uc = SyncGithub(
        SqlExternalAccountRepository(session),
        SqlSyncRunsRepository(session),
        SqlAlchemyProjectRepository(session),
        SqlAlchemySkillRepository(session),
        SqlAlchemyInterestRepository(session),
        SqlAlchemyExperienceRepository(session),
    )
    uow = _new_uow(session)
    return await uc.execute(user_id=str(user_id), uow=uow)


async def _h_disconnect_account(*, session, user_id, client_id, args):
    from src.integrations.application.connect_disconnect import DisconnectAccount
    from src.integrations.infrastructure.repositories import SqlExternalAccountRepository

    uc = DisconnectAccount(SqlExternalAccountRepository(session))
    uow = _new_uow(session)
    r = await uc.execute(user_id=str(user_id), provider=args["provider"], uow=uow)
    if r.is_failure:
        raise r.error  # type: ignore[union-attr]
    return {"disconnected": True}


async def _h_import_linkedin_zip(*, session, user_id, client_id, args):
    import base64

    from src.integrations.application.linkedin_csv_deep import (
        commit_parsed,
        parse_linkedin_zip,
    )
    from src.integrations.infrastructure.repositories import SqlImportSessionRepository
    from src.universe.interfaces.api.deps import (
        achievement_crud,
        certification_crud,
        course_crud,
        education_crud,
        experience_crud,
        language_crud,
        project_crud,
        skill_crud,
    )

    data = base64.b64decode(args["file_base64"])
    parsed = parse_linkedin_zip(data)
    sessions = SqlImportSessionRepository(session)
    sid = await sessions.create(user_id=user_id, source="linkedin_zip", parsed=parsed)
    if args.get("auto_commit"):
        uow = _new_uow(session)
        summary = await commit_parsed(
            user_id=str(user_id),
            parsed=parsed,
            edu_uc=education_crud(session),
            exp_uc=experience_crud(session),
            skill_uc=skill_crud(session),
            lang_uc=language_crud(session),
            cert_uc=certification_crud(session),
            achievement_uc=achievement_crud(session),
            project_uc=project_crud(session),
            course_uc=course_crud(session),
            uow=uow,
        )
        await sessions.mark_committed(sid)
        return {"session_id": str(sid), "committed": summary}
    return {"session_id": str(sid), "parsed": parsed}


async def _h_import_pdf_cv(*, session, user_id, client_id, args):
    import base64

    from src.integrations.application.pdf_cv_parser import parse_cv_pdf
    from src.integrations.infrastructure.repositories import SqlImportSessionRepository

    data = base64.b64decode(args["file_base64"])
    parsed = (await parse_cv_pdf(data)).model_dump()
    sessions = SqlImportSessionRepository(session)
    sid = await sessions.create(user_id=user_id, source="pdf", parsed=parsed)
    return {"session_id": str(sid), "parsed": parsed}


async def _h_sync_linkedin_dma(*, session, user_id, client_id, args):
    from src.integrations.application.linkedin_sync import SyncLinkedinDma
    from src.integrations.infrastructure.repositories import (
        SqlExternalAccountRepository,
        SqlImportSessionRepository,
        SqlSyncRunsRepository,
    )

    uc = SyncLinkedinDma(
        SqlExternalAccountRepository(session),
        SqlImportSessionRepository(session),
        SqlSyncRunsRepository(session),
    )
    uow = _new_uow(session)
    return await uc.execute(user_id=str(user_id), uow=uow)


async def _h_sync_linkedin_brightdata(*, session, user_id, client_id, args):
    # PRO gating: enforce here (MCP doesn't pass through FastAPI deps)
    from src.identity.infrastructure.repositories import SqlAlchemyUserRepository
    from src.integrations.application.linkedin_sync import SyncLinkedinBrightdata
    from src.integrations.infrastructure.repositories import (
        SqlExternalAccountRepository,
        SqlImportSessionRepository,
        SqlSyncRunsRepository,
    )

    users = SqlAlchemyUserRepository(session)
    user = await users.get_by_id(UUID(str(user_id)))
    if user is None:
        raise PermissionError("User not found")
    if not user.is_pro:
        raise PermissionError("PRO tier required for Bright Data LinkedIn sync")

    uc = SyncLinkedinBrightdata(
        SqlExternalAccountRepository(session),
        SqlImportSessionRepository(session),
        SqlSyncRunsRepository(session),
    )
    uow = _new_uow(session)
    return await uc.execute(
        user_id=str(user_id),
        linkedin_url=args.get("linkedin_url"),
        fresh=bool(args.get("fresh")),
        uow=uow,
    )


async def _h_commit_import_session(*, session, user_id, client_id, args):
    """Commit a previously-opened import session (LinkedIn DMA / Bright Data / PDF / ZIP).

    Args: { session_id, selection? }
    """
    from src.integrations.application.linkedin_csv_deep import commit_parsed
    from src.integrations.application.pdf_cv_parser import commit_selection
    from src.integrations.infrastructure.repositories import SqlImportSessionRepository
    from src.universe.interfaces.api.deps import (
        achievement_crud,
        certification_crud,
        course_crud,
        education_crud,
        experience_crud,
        language_crud,
        project_crud,
        skill_crud,
    )

    sessions = SqlImportSessionRepository(session)
    sid_str = args["session_id"]
    sess = await sessions.get(UUID(str(user_id)), UUID(sid_str))
    if sess is None:
        raise ValueError("Import session not found")

    selection = args.get("selection")
    uow = _new_uow(session)
    if selection:
        summary = await commit_selection(
            user_id=str(user_id),
            parsed=sess["parsed"],
            selection=selection,
            edu_uc=education_crud(session),
            exp_uc=experience_crud(session),
            skill_uc=skill_crud(session),
            lang_uc=language_crud(session),
            cert_uc=certification_crud(session),
            project_uc=project_crud(session),
            achievement_uc=achievement_crud(session),
            uow=uow,
        )
    else:
        summary = await commit_parsed(
            user_id=str(user_id),
            parsed=sess["parsed"],
            edu_uc=education_crud(session),
            exp_uc=experience_crud(session),
            skill_uc=skill_crud(session),
            lang_uc=language_crud(session),
            cert_uc=certification_crud(session),
            achievement_uc=achievement_crud(session),
            project_uc=project_crud(session),
            course_uc=course_crud(session),
            uow=uow,
        )
    await sessions.mark_committed(UUID(sid_str))
    return {"committed": summary}


async def _h_set_user_tier(*, session, user_id, client_id, args):
    from src.identity.application.use_cases import SetUserTier
    from src.identity.infrastructure.repositories import SqlAlchemyUserRepository

    uc = SetUserTier(SqlAlchemyUserRepository(session))
    uow = _new_uow(session)
    r = await uc.execute(user_id=str(user_id), tier=args["tier"], uow=uow)
    if r.is_failure:
        raise r.error  # type: ignore[union-attr]
    return {
        "tier": r.value.tier,
        "tier_updated_at": r.value.tier_updated_at,
    }


async def _h_get_user_tier(*, session, user_id, client_id, args):
    from src.identity.infrastructure.repositories import SqlAlchemyUserRepository

    users = SqlAlchemyUserRepository(session)
    user = await users.get_by_id(UUID(str(user_id)))
    if user is None:
        raise ValueError("User not found")
    return {
        "tier": user.tier,
        "is_pro": user.is_pro,
        "tier_updated_at": user.tier_updated_at.isoformat() if user.tier_updated_at else None,
    }


# --- Suggestions + Reminders ----------------------------------------------


async def _h_suggest_profile_updates(*, session, user_id, client_id, args):
    from src.universe.application.suggestions import GenerateSuggestions
    from src.universe.infrastructure.repositories import (
        SqlAlchemyCareerPreferencesRepository,
        SqlAlchemyCertificationRepository,
        SqlAlchemyEducationRepository,
        SqlAlchemyExperienceRepository,
        SqlAlchemyLanguageRepository,
        SqlAlchemyProjectRepository,
        SqlAlchemySkillRepository,
    )

    uc = GenerateSuggestions(
        session,
        SqlAlchemyEducationRepository(session),
        SqlAlchemyExperienceRepository(session),
        SqlAlchemyProjectRepository(session),
        SqlAlchemySkillRepository(session),
        SqlAlchemyCertificationRepository(session),
        SqlAlchemyLanguageRepository(session),
        SqlAlchemyCareerPreferencesRepository(session),
    )
    return await uc.execute(user_id=str(user_id))


async def _h_list_suggestions(*, session, user_id, client_id, args):
    from src.universe.application.suggestions import ListSuggestions

    return await ListSuggestions(session).execute(
        user_id=str(user_id),
        status=args.get("status", "pending"),
        limit=int(args.get("limit") or 50),
    )


async def _h_apply_suggestion(*, session, user_id, client_id, args):
    from src.universe.application.suggestions import ActOnSuggestion

    r = await ActOnSuggestion(session).execute(
        user_id=str(user_id),
        suggestion_id=args["suggestion_id"],
        action=args.get("action", "accept"),
    )
    if r.is_failure:
        raise r.error  # type: ignore[union-attr]
    return r.value


async def _h_list_reminders(*, session, user_id, client_id, args):
    from src.universe.application.reminders import ListReminders

    return await ListReminders(session).execute(
        user_id=str(user_id),
        due_within_days=int(args["due_within_days"]) if args.get("due_within_days") is not None else None,
    )


async def _h_dismiss_reminder(*, session, user_id, client_id, args):
    from src.universe.application.reminders import DismissReminder

    r = await DismissReminder(session).execute(
        user_id=str(user_id), reminder_id=args["reminder_id"]
    )
    if r.is_failure:
        raise r.error  # type: ignore[union-attr]
    return {"dismissed": True}


async def _h_scan_reminders(*, session, user_id, client_id, args):
    from src.universe.application.reminders import ScanReminders

    created = await ScanReminders(session).execute(user_id=user_id)
    return {"created": created}


# --- Avatar ----------------------------------------------------------------


async def _h_set_avatar(*, session, user_id, client_id, args):
    import base64

    from src.identity.infrastructure.photo_storage import save_avatar

    data = base64.b64decode(args["file_base64"])
    return await save_avatar(
        session,
        user_id=user_id,
        data=data,
        mime=args.get("mime_type"),
        original_filename=args.get("filename"),
    )


async def _h_get_avatar_url(*, session, user_id, client_id, args):
    from sqlalchemy import select

    from src.shared.config import get_settings
    from src.universe.infrastructure.orm import AvatarOrm

    row = (await session.execute(select(AvatarOrm).where(AvatarOrm.user_id == user_id))).scalar_one_or_none()
    if row is None:
        return {"url": None}
    base = get_settings().canonical_base_url
    return {"url": f"{base}/api/v1/users/me/photo"}


# --- Registry ---------------------------------------------------------------


_ENTITY_SCHEMAS: dict[str, dict[str, Any]] = {
    "education": {
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
    "experience": {
        "required": ["organization", "role"],
        "properties": {
            "organization": {"type": "string"},
            "role": {"type": "string"},
            "start_date": {"type": "string", "format": "date"},
            "end_date": {"type": "string", "format": "date"},
            "is_current": {"type": "boolean"},
            "modality": {"type": "string", "enum": ["remote", "hybrid", "onsite"]},
            "employment_type": {"type": "string"},
            "description": {"type": "string"},
            "highlights": {"type": "array", "items": {"type": "string"}},
            "competences": {"type": "array", "items": {"type": "string"}},
        },
    },
    "project": {
        "required": ["name"],
        "properties": {
            "name": {"type": "string"},
            "description": {"type": "string"},
            "start_date": {"type": "string", "format": "date"},
            "end_date": {"type": "string", "format": "date"},
            "is_current": {"type": "boolean"},
            "role": {"type": "string"},
            "project_type": {"type": "string", "enum": ["side", "oss", "entrepreneurship", "work"]},
            "tech_stack": {"type": "array", "items": {"type": "string"}},
            "highlights": {"type": "array", "items": {"type": "string"}},
            "impact": {"type": "string"},
            "url": {"type": "string"},
        },
    },
    "skill": {
        "required": ["name"],
        "properties": {
            "name": {"type": "string"},
            "category": {"type": "string", "enum": ["hard", "soft", "tool", "methodology"]},
            "level": {"type": "string", "enum": ["basic", "intermediate", "high", "expert"]},
            "years": {"type": "integer"},
            "last_used_year": {"type": "integer"},
        },
    },
    "certification": {
        "required": ["name"],
        "properties": {
            "name": {"type": "string"},
            "issuer": {"type": "string"},
            "issued_on": {"type": "string", "format": "date"},
            "expires_on": {"type": "string", "format": "date"},
            "credential_id": {"type": "string"},
            "verification_url": {"type": "string"},
        },
    },
    "course": {
        "required": ["title"],
        "properties": {
            "title": {"type": "string"},
            "platform": {"type": "string"},
            "started_on": {"type": "string", "format": "date"},
            "completed_on": {"type": "string", "format": "date"},
            "duration_hours": {"type": "integer"},
            "certificate_url": {"type": "string"},
        },
    },
    "language": {
        "required": ["code", "name", "level"],
        "properties": {
            "code": {"type": "string", "minLength": 2, "maxLength": 2},
            "name": {"type": "string"},
            "level": {"type": "string", "enum": ["A1", "A2", "B1", "B2", "C1", "C2", "native"]},
            "certification": {"type": "string"},
        },
    },
    "achievement": {
        "required": ["title"],
        "properties": {
            "title": {"type": "string"},
            "description": {"type": "string"},
            "achieved_on": {"type": "string", "format": "date"},
            "context": {"type": "string"},
            "evidence_url": {"type": "string"},
        },
    },
    "interest": {
        "required": ["name"],
        "properties": {
            "name": {"type": "string"},
            "description": {"type": "string"},
        },
    },
}


def _build_entity_tools() -> dict[str, ToolSpec]:
    out: dict[str, ToolSpec] = {}
    update_id_prop = {"id": {"type": "string", "format": "uuid"}}
    for entity, schema in _ENTITY_SCHEMAS.items():
        out[f"add_{entity}"] = ToolSpec(
            name=f"add_{entity}",
            description=f"Add an {entity} entry to the user's professional universe.",
            input_schema={
                "type": "object",
                "required": schema["required"],
                "properties": schema["properties"],
            },
            handler=_make_add_handler(entity),
            required_scope="universe:write",
        )
        out[f"update_{entity}"] = ToolSpec(
            name=f"update_{entity}",
            description=f"Patch an existing {entity} by id.",
            input_schema={
                "type": "object",
                "required": ["id"],
                "properties": {**update_id_prop, **schema["properties"]},
                "additionalProperties": True,
            },
            handler=_make_update_handler(entity),
            required_scope="universe:write",
        )
        out[f"delete_{entity}"] = ToolSpec(
            name=f"delete_{entity}",
            description=f"Remove an {entity} from the universe.",
            input_schema={
                "type": "object",
                "required": ["id"],
                "properties": update_id_prop,
            },
            handler=_make_delete_handler(entity),
            required_scope="universe:delete",
        )
    return out


_OTHER_TOOLS: dict[str, ToolSpec] = {
    "get_profile": ToolSpec(
        name="get_profile",
        description="Get a section (or all) of the user's professional universe.",
        input_schema={
            "type": "object",
            "properties": {"section": {"type": "string", "enum": ["all", "education", "experience", "skill"], "default": "all"}},
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
    "list_skills": ToolSpec(
        name="list_skills",
        description="List skills filtered by category / min level / min years.",
        input_schema={
            "type": "object",
            "properties": {
                "category": {"type": "string", "enum": ["hard", "soft", "tool", "methodology"]},
                "min_level": {"type": "string", "enum": ["basic", "intermediate", "high", "expert"]},
                "min_years": {"type": "integer"},
            },
        },
        handler=_h_list_skills,
        required_scope="universe:read",
    ),
    "search_universe": ToolSpec(
        name="search_universe",
        description="Semantic search across the user's universe.",
        input_schema={
            "type": "object",
            "required": ["query"],
            "properties": {
                "query": {"type": "string"},
                "top_k": {"type": "integer", "default": 10},
                "entity_types": {"type": "array", "items": {"type": "string"}},
            },
        },
        handler=_h_search,
        required_scope="universe:read",
    ),
    "set_career_preferences": ToolSpec(
        name="set_career_preferences",
        description="Set or patch career preferences (status, salary, modality, etc.).",
        input_schema={
            "type": "object",
            "properties": {
                "status": {"type": "string"},
                "salary_min": {"type": "number"},
                "salary_max": {"type": "number"},
                "salary_currency": {"type": "string"},
                "contract_types": {"type": "array", "items": {"type": "string"}},
                "remote_preference": {"type": "string"},
                "open_to_relocate": {"type": "boolean"},
                "preferred_roles": {"type": "array", "items": {"type": "string"}},
                "discarded_roles": {"type": "array", "items": {"type": "string"}},
                "preferred_competences": {"type": "array", "items": {"type": "string"}},
                "discarded_competences": {"type": "array", "items": {"type": "string"}},
                "motivations": {"type": "string"},
            },
        },
        handler=_h_set_prefs,
        required_scope="preferences:write",
    ),
    "get_career_preferences": ToolSpec(
        name="get_career_preferences",
        description="Read current career preferences.",
        input_schema={"type": "object", "properties": {}},
        handler=_h_get_prefs,
        required_scope="preferences:read",
    ),
    "update_universe_header": ToolSpec(
        name="update_universe_header",
        description="Set headline, summary, current_status, photo URL.",
        input_schema={
            "type": "object",
            "properties": {
                "headline": {"type": "string"},
                "summary": {"type": "string"},
                "photo_url": {"type": "string"},
                "current_status": {"type": "string"},
            },
        },
        handler=_h_update_header,
        required_scope="universe:write",
    ),
    "mark_reviewed": ToolSpec(
        name="mark_reviewed",
        description="Touch last_reviewed_at on an entity.",
        input_schema={
            "type": "object",
            "required": ["entity_type", "entity_id"],
            "properties": {
                "entity_type": {"type": "string"},
                "entity_id": {"type": "string", "format": "uuid"},
            },
        },
        handler=_h_mark_reviewed,
        required_scope="universe:write",
    ),
    "link_evidence": ToolSpec(
        name="link_evidence",
        description="Link a skill to an evidence entity (experience/project/etc).",
        input_schema={
            "type": "object",
            "required": ["skill_id", "evidence_entity_type", "evidence_entity_id"],
            "properties": {
                "skill_id": {"type": "string", "format": "uuid"},
                "evidence_entity_type": {"type": "string"},
                "evidence_entity_id": {"type": "string", "format": "uuid"},
                "weight": {"type": "number", "default": 1.0},
                "notes": {"type": "string"},
            },
        },
        handler=_h_link_evidence,
        required_scope="evidence:write",
    ),
    "get_activity": ToolSpec(
        name="get_activity",
        description="Return recent universe activity.",
        input_schema={
            "type": "object",
            "properties": {
                "limit": {"type": "integer", "default": 50},
                "since": {"type": "string", "format": "date-time"},
                "event_types": {"type": "array", "items": {"type": "string"}},
            },
        },
        handler=_h_get_activity,
        required_scope="universe:read",
    ),
    "match_job_to_profile": ToolSpec(
        name="match_job_to_profile",
        description="Score a JD against the user's universe.",
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
        description="Generate an ATS-adapted CV (PDF + DOCX + JSON Resume).",
        input_schema={
            "type": "object",
            "properties": {
                "job_url": {"type": "string"},
                "job_description": {"type": "string"},
                "template": {"type": "string", "default": "ats-classic"},
                "language": {"type": "string", "enum": ["es", "en"], "default": "es"},
                "tone": {"type": "string"},
                "length": {"type": "string", "enum": ["1-page", "2-page"]},
            },
        },
        handler=_h_generate_cv,
        required_scope="documents:generate",
    ),
    "list_documents": ToolSpec(
        name="list_documents",
        description="List generated CVs / cover letters.",
        input_schema={
            "type": "object",
            "properties": {
                "kind": {"type": "string", "enum": ["cv", "cover_letter"]},
                "limit": {"type": "integer", "default": 20},
            },
        },
        handler=_h_list_documents,
        required_scope="documents:read",
    ),
    "get_document": ToolSpec(
        name="get_document",
        description="Get a single document by id.",
        input_schema={
            "type": "object",
            "required": ["id"],
            "properties": {"id": {"type": "string", "format": "uuid"}},
        },
        handler=_h_get_document,
        required_scope="documents:read",
    ),
    "share_document": ToolSpec(
        name="share_document",
        description="Create a public share token for a document.",
        input_schema={
            "type": "object",
            "required": ["id"],
            "properties": {
                "id": {"type": "string", "format": "uuid"},
                "expires_in_days": {"type": "integer", "default": 30},
            },
        },
        handler=_h_share_document,
        required_scope="documents:read",
    ),
    "list_connections": ToolSpec(
        name="list_connections",
        description="List external accounts connected to this universe.",
        input_schema={"type": "object", "properties": {}},
        handler=_h_list_connections,
        required_scope="integrations:read",
    ),
    "sync_github": ToolSpec(
        name="sync_github",
        description="Trigger an immediate GitHub sync.",
        input_schema={"type": "object", "properties": {"force_full": {"type": "boolean", "default": False}}},
        handler=_h_sync_github,
        required_scope="integrations:write",
    ),
    "disconnect_account": ToolSpec(
        name="disconnect_account",
        description="Disconnect an external account.",
        input_schema={
            "type": "object",
            "required": ["provider"],
            "properties": {"provider": {"type": "string"}},
        },
        handler=_h_disconnect_account,
        required_scope="integrations:write",
    ),
    "import_linkedin_zip": ToolSpec(
        name="import_linkedin_zip",
        description="Parse a LinkedIn data ZIP (base64) and optionally commit entities.",
        input_schema={
            "type": "object",
            "required": ["file_base64"],
            "properties": {
                "file_base64": {"type": "string"},
                "auto_commit": {"type": "boolean", "default": False},
            },
        },
        handler=_h_import_linkedin_zip,
        required_scope="universe:write",
    ),
    "import_pdf_cv": ToolSpec(
        name="import_pdf_cv",
        description="Parse a CV PDF (base64) into a structured payload (review before commit).",
        input_schema={
            "type": "object",
            "required": ["file_base64"],
            "properties": {"file_base64": {"type": "string"}},
        },
        handler=_h_import_pdf_cv,
        required_scope="universe:write",
    ),
    "suggest_profile_updates": ToolSpec(
        name="suggest_profile_updates",
        description="Generate fresh suggestions (skills to add, expiring certs, stale entries…).",
        input_schema={"type": "object", "properties": {"limit": {"type": "integer", "default": 20}}},
        handler=_h_suggest_profile_updates,
        required_scope="suggestions:write",
    ),
    "list_suggestions": ToolSpec(
        name="list_suggestions",
        description="List pending suggestions.",
        input_schema={
            "type": "object",
            "properties": {
                "status": {"type": "string", "default": "pending"},
                "limit": {"type": "integer", "default": 50},
            },
        },
        handler=_h_list_suggestions,
        required_scope="suggestions:read",
    ),
    "apply_suggestion": ToolSpec(
        name="apply_suggestion",
        description="Accept or reject a suggestion.",
        input_schema={
            "type": "object",
            "required": ["suggestion_id", "action"],
            "properties": {
                "suggestion_id": {"type": "string", "format": "uuid"},
                "action": {"type": "string", "enum": ["accept", "reject"]},
            },
        },
        handler=_h_apply_suggestion,
        required_scope="suggestions:write",
    ),
    "list_reminders": ToolSpec(
        name="list_reminders",
        description="List active reminders.",
        input_schema={
            "type": "object",
            "properties": {"due_within_days": {"type": "integer"}},
        },
        handler=_h_list_reminders,
        required_scope="reminders:read",
    ),
    "dismiss_reminder": ToolSpec(
        name="dismiss_reminder",
        description="Dismiss a reminder.",
        input_schema={
            "type": "object",
            "required": ["reminder_id"],
            "properties": {"reminder_id": {"type": "string", "format": "uuid"}},
        },
        handler=_h_dismiss_reminder,
        required_scope="reminders:write",
    ),
    "scan_reminders": ToolSpec(
        name="scan_reminders",
        description="Run reminder scan (cert expiry, course stale, etc).",
        input_schema={"type": "object", "properties": {}},
        handler=_h_scan_reminders,
        required_scope="reminders:write",
    ),
    "set_avatar": ToolSpec(
        name="set_avatar",
        description="Upload profile photo (base64-encoded JPG/PNG/WebP, max 5 MB).",
        input_schema={
            "type": "object",
            "required": ["file_base64"],
            "properties": {
                "file_base64": {"type": "string"},
                "mime_type": {"type": "string"},
                "filename": {"type": "string"},
            },
        },
        handler=_h_set_avatar,
        required_scope="universe:write",
    ),
    "get_avatar_url": ToolSpec(
        name="get_avatar_url",
        description="Return the URL of the user's profile photo (or null).",
        input_schema={"type": "object", "properties": {}},
        handler=_h_get_avatar_url,
        required_scope="universe:read",
    ),
    "sync_linkedin_dma": ToolSpec(
        name="sync_linkedin_dma",
        description=(
            "Pull profile data via LinkedIn DMA 3rd-party API (EEA users, free) "
            "and open an import session. Returns the parsed payload — review and "
            "commit via `commit_import_session`. Uses a deterministic fixture in "
            "dev when `LINKEDIN_DMA_ENABLED=false`."
        ),
        input_schema={"type": "object", "properties": {}},
        handler=_h_sync_linkedin_dma,
        required_scope="integrations:write",
    ),
    "sync_linkedin_brightdata": ToolSpec(
        name="sync_linkedin_brightdata",
        description=(
            "Pull profile data via Bright Data LinkedIn People Profile API "
            "(global, paid). PRO tier required. Returns parsed payload — "
            "review and commit via `commit_import_session`. `fresh=true` "
            "forces a non-cached lookup (more expensive, ~$0.50-1)."
        ),
        input_schema={
            "type": "object",
            "properties": {
                "linkedin_url": {"type": "string", "description": "Public LinkedIn profile URL"},
                "fresh": {"type": "boolean", "default": False},
            },
        },
        handler=_h_sync_linkedin_brightdata,
        required_scope="integrations:write",
    ),
    "commit_import_session": ToolSpec(
        name="commit_import_session",
        description=(
            "Commit a previously-opened import session (linkedin_dma, "
            "linkedin_brightdata, linkedin_zip, pdf). Optional `selection` to "
            "commit only a subset of items per section."
        ),
        input_schema={
            "type": "object",
            "required": ["session_id"],
            "properties": {
                "session_id": {"type": "string", "format": "uuid"},
                "selection": {
                    "type": "object",
                    "additionalProperties": {
                        "type": "array",
                        "items": {"type": "integer"},
                    },
                },
            },
        },
        handler=_h_commit_import_session,
        required_scope="universe:write",
    ),
    "set_user_tier": ToolSpec(
        name="set_user_tier",
        description=(
            "Set the user's subscription tier (free | pro). In production this "
            "is driven by Stripe webhooks; today it's exposed for dev/admin use."
        ),
        input_schema={
            "type": "object",
            "required": ["tier"],
            "properties": {"tier": {"type": "string", "enum": ["free", "pro"]}},
        },
        handler=_h_set_user_tier,
        required_scope="account:write",
    ),
    "get_user_tier": ToolSpec(
        name="get_user_tier",
        description="Return current subscription tier.",
        input_schema={"type": "object", "properties": {}},
        handler=_h_get_user_tier,
        required_scope="account:read",
    ),
}


TOOLS: dict[str, ToolSpec] = {**_build_entity_tools(), **_OTHER_TOOLS}
