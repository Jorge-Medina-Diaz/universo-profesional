"""Handler implementations behind the MCP tool registry.

Split out of `tools.py`, which had grown to 1544 lines by holding ~940 lines
of handler bodies alongside the declarative registry that references them.
Every handler delegates to the same use cases the REST routes use — there is
no duplicate business logic here, only the MCP-shaped adapter around it.
"""
from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.universe.application.registry import CrudRegistry


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


async def _h_get_profile(
    *,
    session: AsyncSession,
    user_id: UUID,
    client_id: str | None,
    args: dict[str, Any],
) -> Any:
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


async def _h_summary(
    *,
    session: AsyncSession,
    user_id: UUID,
    client_id: str | None,
    args: dict[str, Any],
) -> Any:
    return await _h_get_profile(session=session, user_id=user_id, client_id=client_id, args={})


async def _h_list_skills(
    *,
    session: AsyncSession,
    user_id: UUID,
    client_id: str | None,
    args: dict[str, Any],
) -> Any:
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


async def _h_search(
    *,
    session: AsyncSession,
    user_id: UUID,
    client_id: str | None,
    args: dict[str, Any],
) -> Any:
    from src.universe.application.use_cases import SearchUniverse

    deps = _session_only_deps(session)
    uc = SearchUniverse(deps["search"], deps["embedder"])
    return await uc.execute(
        user_id=str(user_id),
        query=args["query"],
        top_k=int(args.get("top_k") or 10),
        entity_types=args.get("entity_types"),
    )


# --- Universe write (CRUD per entity, via registry) -------------------------


def _build_crud(session: AsyncSession, entity: str) -> Any:
    deps = _session_only_deps(session)
    crud_cls = CrudRegistry.get_crud_class(entity)
    repo = deps[CrudRegistry.get_repo_key(entity)]
    return crud_cls(repo, deps["scheduler"])


def _make_add_handler(entity: str) -> Any:
    async def handler(
        *,
        session: AsyncSession,
        user_id: UUID,
        client_id: str | None,
        args: dict[str, Any],
    ) -> Any:
        uc_inst = _build_crud(session, entity)
        uow = _new_uow(session)
        r = await uc_inst.add(user_id=str(user_id), payload=dict(args), uow=uow)
        if r.is_failure:
            raise r.error
        return r.value

    return handler


def _make_update_handler(entity: str) -> Any:
    async def handler(
        *,
        session: AsyncSession,
        user_id: UUID,
        client_id: str | None,
        args: dict[str, Any],
    ) -> Any:
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
            raise r.error
        return r.value

    return handler


def _make_delete_handler(entity: str) -> Any:
    async def handler(
        *,
        session: AsyncSession,
        user_id: UUID,
        client_id: str | None,
        args: dict[str, Any],
    ) -> Any:
        uc_inst = _build_crud(session, entity)
        uow = _new_uow(session)
        r = await uc_inst.delete(user_id=str(user_id), entity_id=args["id"], uow=uow)
        if r.is_failure:
            raise r.error
        return {"deleted": True}

    return handler


# --- Preferences + header ---------------------------------------------------


async def _h_set_prefs(
    *,
    session: AsyncSession,
    user_id: UUID,
    client_id: str | None,
    args: dict[str, Any],
) -> Any:
    from src.universe.application.use_cases import SetCareerPreferences

    deps = _session_only_deps(session)
    return await SetCareerPreferences(deps["prefs_repo"]).execute(
        user_id=str(user_id), patch=dict(args)
    )


async def _h_get_prefs(
    *,
    session: AsyncSession,
    user_id: UUID,
    client_id: str | None,
    args: dict[str, Any],
) -> Any:
    from src.universe.application.use_cases import GetCareerPreferences

    deps = _session_only_deps(session)
    return await GetCareerPreferences(deps["prefs_repo"]).execute(user_id=str(user_id))


async def _h_update_header(
    *,
    session: AsyncSession,
    user_id: UUID,
    client_id: str | None,
    args: dict[str, Any],
) -> Any:
    from src.universe.application.use_cases import UpdateUniverseHeader

    deps = _session_only_deps(session)
    uc = UpdateUniverseHeader(deps["univ_repo"])
    uow = _new_uow(session)
    return await uc.execute(user_id=str(user_id), patch=dict(args), uow=uow)


# --- Mark reviewed + Evidence + Activity -----------------------------------


async def _h_mark_reviewed(
    *,
    session: AsyncSession,
    user_id: UUID,
    client_id: str | None,
    args: dict[str, Any],
) -> Any:
    from src.universe.application.use_cases import MarkReviewed

    r = await MarkReviewed(session).execute(
        user_id=str(user_id),
        entity_type=args["entity_type"],
        entity_id=args["entity_id"],
    )
    if r.is_failure:
        raise r.error
    return r.value


async def _h_link_evidence(
    *,
    session: AsyncSession,
    user_id: UUID,
    client_id: str | None,
    args: dict[str, Any],
) -> Any:
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
        raise r.error
    return r.value


async def _h_get_activity(
    *,
    session: AsyncSession,
    user_id: UUID,
    client_id: str | None,
    args: dict[str, Any],
) -> Any:
    from src.universe.application.use_cases import GetActivity

    return await GetActivity(session).execute(
        user_id=str(user_id),
        limit=int(args.get("limit") or 50),
        since=args.get("since"),
        event_types=args.get("event_types"),
    )


# --- Match job + Generate CV ------------------------------------------------


async def _h_match_job(
    *,
    session: AsyncSession,
    user_id: UUID,
    client_id: str | None,
    args: dict[str, Any],
) -> Any:
    from src.documents.application.match_scoring import compute_match_breakdown
    from src.documents.infrastructure.job_parser import MockJobParser

    parser = MockJobParser()
    parsed = await parser.parse(url=args.get("job_url"), description=args.get("job_description"))
    deps = _session_only_deps(session)
    jd_text = parsed.get("description_raw") or " ".join(str(v) for v in parsed.values())
    vec = await deps["embedder"].embed(jd_text)
    retrieved = await deps["search"].search(user_id=user_id, embedding=vec, top_k=20)
    your_skills = [s.name for s in await deps["skill_repo"].list(user_id)]
    breakdown = compute_match_breakdown(
        retrieved=retrieved,
        needed_keywords=list(parsed.get("ats_keywords", [])),
        your_skills=your_skills,
    )
    return {
        **breakdown,
        "parsed_jd": parsed,
        "retrieved": retrieved[:10],
    }


async def _h_generate_cv(
    *,
    session: AsyncSession,
    user_id: UUID,
    client_id: str | None,
    args: dict[str, Any],
) -> Any:
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

    # NOTE: the daily `mcp_call` quota is enforced centrally in mcp_router for
    # every tool (check before + increment after success), so it is NOT handled
    # here anymore — that avoids double-counting and the previous "increment
    # before generation" bug. We only enforce the CV-specific monthly cap here.
    quota = CheckQuota(
        SqlAlchemySubscriptionRepository(session),
        SqlAlchemyQuotaRepository(session),
    )
    qr2 = await quota.execute(user_id=str(user_id), resource="cv_generated")
    if qr2.is_failure:
        raise qr2.error

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
        raise r.error
    await quota.increment(user_id=str(user_id), resource="cv_generated")
    dto = r.value
    return {
        "document_id": dto.document_id,
        "pdf_url": dto.pdf_url,
        "docx_url": dto.docx_url,
        "json_resume": dto.json_resume,
    }


# --- Documents read ---------------------------------------------------------


async def _h_list_documents(
    *,
    session: AsyncSession,
    user_id: UUID,
    client_id: str | None,
    args: dict[str, Any],
) -> Any:
    from src.documents.application.use_cases import ListDocuments
    from src.documents.infrastructure.repositories import SqlAlchemyDocumentRepository

    return await ListDocuments(SqlAlchemyDocumentRepository(session)).execute(
        user_id=str(user_id), kind=args.get("kind"), limit=int(args.get("limit") or 20)
    )


async def _h_get_document(
    *,
    session: AsyncSession,
    user_id: UUID,
    client_id: str | None,
    args: dict[str, Any],
) -> Any:
    from src.documents.application.use_cases import GetDocument
    from src.documents.infrastructure.repositories import SqlAlchemyDocumentRepository

    r = await GetDocument(SqlAlchemyDocumentRepository(session)).execute(
        user_id=str(user_id), document_id=args["id"]
    )
    if r.is_failure:
        raise r.error
    return r.value


async def _h_share_document(
    *,
    session: AsyncSession,
    user_id: UUID,
    client_id: str | None,
    args: dict[str, Any],
) -> Any:
    from src.documents.application.use_cases import ShareDocument
    from src.documents.infrastructure.repositories import SqlAlchemyDocumentRepository

    r = await ShareDocument(SqlAlchemyDocumentRepository(session)).execute(
        user_id=str(user_id),
        document_id=args["id"],
        expires_in_days=int(args.get("expires_in_days") or 30),
    )
    if r.is_failure:
        raise r.error
    return r.value


# --- Integrations -----------------------------------------------------------


async def _h_list_connections(
    *,
    session: AsyncSession,
    user_id: UUID,
    client_id: str | None,
    args: dict[str, Any],
) -> Any:
    from src.integrations.application.connect_disconnect import ListConnections
    from src.integrations.infrastructure.repositories import SqlExternalAccountRepository

    return await ListConnections(SqlExternalAccountRepository(session)).execute(
        user_id=str(user_id)
    )


async def _h_sync_github(
    *,
    session: AsyncSession,
    user_id: UUID,
    client_id: str | None,
    args: dict[str, Any],
) -> Any:
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
        session=session,
    )
    uow = _new_uow(session)
    return await uc.execute(user_id=str(user_id), uow=uow)


async def _h_disconnect_account(
    *,
    session: AsyncSession,
    user_id: UUID,
    client_id: str | None,
    args: dict[str, Any],
) -> Any:
    from src.integrations.application.connect_disconnect import DisconnectAccount
    from src.integrations.infrastructure.repositories import SqlExternalAccountRepository

    uc = DisconnectAccount(SqlExternalAccountRepository(session))
    uow = _new_uow(session)
    r = await uc.execute(user_id=str(user_id), provider=args["provider"], uow=uow)
    if r.is_failure:
        raise r.error
    return {"disconnected": True}


async def _h_import_linkedin_zip(
    *,
    session: AsyncSession,
    user_id: UUID,
    client_id: str | None,
    args: dict[str, Any],
) -> Any:
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


async def _h_import_pdf_cv(
    *,
    session: AsyncSession,
    user_id: UUID,
    client_id: str | None,
    args: dict[str, Any],
) -> Any:
    import base64

    from src.integrations.application.pdf_cv_parser import parse_cv_pdf
    from src.integrations.infrastructure.repositories import SqlImportSessionRepository

    data = base64.b64decode(args["file_base64"])
    parsed = (await parse_cv_pdf(data)).model_dump()
    sessions = SqlImportSessionRepository(session)
    sid = await sessions.create(user_id=user_id, source="pdf", parsed=parsed)
    return {"session_id": str(sid), "parsed": parsed}


async def _h_sync_linkedin_dma(
    *,
    session: AsyncSession,
    user_id: UUID,
    client_id: str | None,
    args: dict[str, Any],
) -> Any:
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


async def _h_sync_linkedin_brightdata(
    *,
    session: AsyncSession,
    user_id: UUID,
    client_id: str | None,
    args: dict[str, Any],
) -> Any:
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
    if not user.is_paying:
        raise PermissionError("A paid plan is required for Bright Data LinkedIn sync")

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


async def _h_commit_import_session(
    *,
    session: AsyncSession,
    user_id: UUID,
    client_id: str | None,
    args: dict[str, Any],
) -> Any:
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


async def _h_set_user_tier(
    *,
    session: AsyncSession,
    user_id: UUID,
    client_id: str | None,
    args: dict[str, Any],
) -> Any:
    from src.identity.application.use_cases import SetUserTier
    from src.identity.infrastructure.repositories import SqlAlchemyUserRepository
    from src.shared.config import get_settings

    # Privilege-escalation guard: a free user could otherwise call this MCP tool
    # to grant themselves a paid tier. Tier is Stripe-derived in prod; refuse
    # here outside dev/test (defence-in-depth — the tool is also unregistered in
    # prod, see _assemble_tools).
    if get_settings().is_prod:
        raise PermissionError("set_user_tier is disabled in production")

    uc = SetUserTier(SqlAlchemyUserRepository(session))
    uow = _new_uow(session)
    r = await uc.execute(user_id=str(user_id), tier=args["tier"], uow=uow)
    if r.is_failure:
        raise r.error
    return {
        "tier": r.value.tier,
        "tier_updated_at": r.value.tier_updated_at,
    }


async def _h_get_user_tier(
    *,
    session: AsyncSession,
    user_id: UUID,
    client_id: str | None,
    args: dict[str, Any],
) -> Any:
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


async def _h_suggest_profile_updates(
    *,
    session: AsyncSession,
    user_id: UUID,
    client_id: str | None,
    args: dict[str, Any],
) -> Any:
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


async def _h_list_suggestions(
    *,
    session: AsyncSession,
    user_id: UUID,
    client_id: str | None,
    args: dict[str, Any],
) -> Any:
    from src.universe.application.suggestions import ListSuggestions

    return await ListSuggestions(session).execute(
        user_id=str(user_id),
        status=args.get("status", "pending"),
        limit=int(args.get("limit") or 50),
    )


async def _h_apply_suggestion(
    *,
    session: AsyncSession,
    user_id: UUID,
    client_id: str | None,
    args: dict[str, Any],
) -> Any:
    from src.universe.application.suggestions import ActOnSuggestion

    r = await ActOnSuggestion(session).execute(
        user_id=str(user_id),
        suggestion_id=args["suggestion_id"],
        action=args.get("action", "accept"),
    )
    if r.is_failure:
        raise r.error
    return r.value


async def _h_list_reminders(
    *,
    session: AsyncSession,
    user_id: UUID,
    client_id: str | None,
    args: dict[str, Any],
) -> Any:
    from src.universe.application.reminders import ListReminders

    return await ListReminders(session).execute(
        user_id=str(user_id),
        due_within_days=int(args["due_within_days"]) if args.get("due_within_days") is not None else None,
    )


async def _h_dismiss_reminder(
    *,
    session: AsyncSession,
    user_id: UUID,
    client_id: str | None,
    args: dict[str, Any],
) -> Any:
    from src.universe.application.reminders import DismissReminder

    r = await DismissReminder(session).execute(
        user_id=str(user_id), reminder_id=args["reminder_id"]
    )
    if r.is_failure:
        raise r.error
    return {"dismissed": True}


async def _h_scan_reminders(
    *,
    session: AsyncSession,
    user_id: UUID,
    client_id: str | None,
    args: dict[str, Any],
) -> Any:
    from src.universe.application.reminders import ScanReminders

    created = await ScanReminders(session).execute(user_id=user_id)
    return {"created": created}


# --- Avatar ----------------------------------------------------------------


async def _h_set_avatar(
    *,
    session: AsyncSession,
    user_id: UUID,
    client_id: str | None,
    args: dict[str, Any],
) -> Any:
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


async def _h_get_avatar_url(
    *,
    session: AsyncSession,
    user_id: UUID,
    client_id: str | None,
    args: dict[str, Any],
) -> Any:
    from sqlalchemy import select

    from src.shared.config import get_settings
    from src.universe.application.ports.orm import AvatarOrm

    row = (await session.execute(select(AvatarOrm).where(AvatarOrm.user_id == user_id))).scalar_one_or_none()
    if row is None:
        return {"url": None}
    base = get_settings().canonical_base_url
    return {"url": f"{base}/api/v1/users/me/photo"}


