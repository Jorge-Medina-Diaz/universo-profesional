"""/api/v1/integrations/* — GitHub OAuth + sync, LinkedIn ZIP, PDF CV import."""
from __future__ import annotations

import urllib.parse
from typing import Annotated, Any

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import RedirectResponse
from pydantic import BaseModel

from src.identity.interfaces.api.deps import CurrentUserId, SessionDep
from src.integrations.application.connect_disconnect import (
    ConnectGithub,
    DisconnectAccount,
    ListConnections,
)
from src.integrations.application.github_sync import SyncGithub
from src.integrations.application.linkedin_csv_deep import (
    commit_parsed,
    parse_linkedin_zip,
)
from src.integrations.application.pdf_cv_parser import (
    ParsedCv,
    commit_selection,
    parse_cv_pdf,
)
from src.integrations.infrastructure.repositories import (
    SqlExternalAccountRepository,
    SqlImportSessionRepository,
    SqlSyncRunsRepository,
)
from src.shared.config import get_settings
from src.shared.uow import unit_of_work

router = APIRouter()


# ---------- GitHub ---------- #


@router.get("/github/authorize")
async def github_authorize(user_id: CurrentUserId) -> dict[str, str]:
    """Return the GitHub OAuth authorize URL for the user to visit."""
    s = get_settings()
    if not s.github_client_id:
        raise HTTPException(
            status_code=503,
            detail="GitHub integration not configured (GITHUB_CLIENT_ID missing).",
        )
    redirect_uri = f"{s.canonical_base_url}/api/v1/integrations/github/callback"
    params = {
        "client_id": s.github_client_id,
        "redirect_uri": redirect_uri,
        "scope": "read:user public_repo read:org user:email",
        "state": user_id,
        "allow_signup": "false",
    }
    url = "https://github.com/login/oauth/authorize?" + urllib.parse.urlencode(params)
    return {"authorize_url": url}


@router.get("/github/callback")
async def github_callback(
    code: str,
    state: str,
    session: SessionDep,
) -> RedirectResponse:
    """OAuth callback — we use `state` to carry the user_id (signed in v1; raw in MVP)."""
    s = get_settings()
    redirect_uri = f"{s.canonical_base_url}/api/v1/integrations/github/callback"
    accounts = SqlExternalAccountRepository(session)
    uc = ConnectGithub(accounts)
    async with unit_of_work(session) as uow:
        try:
            await uc.execute(user_id=state, code=code, redirect_uri=redirect_uri, uow=uow)
            await uow.commit()
        except Exception as exc:  # noqa: BLE001
            return RedirectResponse(
                url=f"{s.frontend_base_url}/#/connections?error={urllib.parse.quote(str(exc))}",
                status_code=302,
            )
    return RedirectResponse(
        url=f"{s.frontend_base_url}/#/connections?connected=github",
        status_code=302,
    )


@router.post("/github/sync")
async def github_sync(user_id: CurrentUserId, session: SessionDep) -> dict[str, Any]:
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
    async with unit_of_work(session) as uow:
        result = await uc.execute(user_id=user_id, uow=uow)
        await uow.commit()
    return result


@router.delete("/github")
async def github_disconnect(user_id: CurrentUserId, session: SessionDep) -> dict[str, bool]:
    uc = DisconnectAccount(SqlExternalAccountRepository(session))
    async with unit_of_work(session) as uow:
        r = await uc.execute(user_id=user_id, provider="github", uow=uow)
        if r.is_failure:
            raise r.error  # type: ignore[union-attr]
        await uow.commit()
    return {"ok": True}


# ---------- Connections list ---------- #


@router.get("")
async def list_connections(user_id: CurrentUserId, session: SessionDep) -> dict[str, Any]:
    uc = ListConnections(SqlExternalAccountRepository(session))
    return {"connections": await uc.execute(user_id=user_id)}


@router.get("/sync-runs")
async def list_sync_runs(
    user_id: CurrentUserId, session: SessionDep, limit: int = 10
) -> dict[str, Any]:
    runs = SqlSyncRunsRepository(session)
    return {"runs": await runs.list_for_user(__import__("uuid").UUID(user_id), limit=limit)}


# ---------- LinkedIn deep ZIP ---------- #


@router.post("/linkedin/zip/parse")
async def linkedin_zip_parse(
    user_id: CurrentUserId,
    session: SessionDep,
    file: UploadFile = File(...),
) -> dict[str, Any]:
    """Parse LinkedIn ZIP into a structured payload — does NOT commit."""
    contents = await file.read()
    parsed = parse_linkedin_zip(contents)
    sessions = SqlImportSessionRepository(session)
    async with unit_of_work(session) as uow:
        sid = await sessions.create(
            user_id=__import__("uuid").UUID(user_id), source="linkedin_zip", parsed=parsed
        )
        await uow.commit()
    return {"session_id": str(sid), "parsed": parsed}


@router.post("/linkedin/zip/commit")
async def linkedin_zip_commit(
    user_id: CurrentUserId,
    session: SessionDep,
    body: dict[str, Any],
) -> dict[str, Any]:
    from uuid import UUID

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
    sess = await sessions.get(UUID(user_id), UUID(body["session_id"]))
    if sess is None:
        raise HTTPException(status_code=404, detail="Import session not found")

    edu_uc = education_crud(session)
    exp_uc = experience_crud(session)
    skill_uc = skill_crud(session)
    lang_uc = language_crud(session)
    cert_uc = certification_crud(session)
    ach_uc = achievement_crud(session)
    proj_uc = project_crud(session)
    course_uc = course_crud(session)

    async with unit_of_work(session) as uow:
        summary = await commit_parsed(
            user_id=user_id,
            parsed=sess["parsed"],
            edu_uc=edu_uc,
            exp_uc=exp_uc,
            skill_uc=skill_uc,
            lang_uc=lang_uc,
            cert_uc=cert_uc,
            achievement_uc=ach_uc,
            project_uc=proj_uc,
            course_uc=course_uc,
            uow=uow,
        )
        await sessions.mark_committed(UUID(body["session_id"]))
        await uow.commit()
    return {"committed": summary}


# ---------- PDF CV ---------- #


class CommitPdfBody(BaseModel):
    session_id: str
    selection: dict[str, list[int]] | None = None  # section → list of indices


@router.post("/pdf/parse")
async def pdf_parse(
    user_id: CurrentUserId,
    session: SessionDep,
    file: UploadFile = File(...),
) -> dict[str, Any]:
    contents = await file.read()
    parsed_obj: ParsedCv = await parse_cv_pdf(contents)
    parsed = parsed_obj.model_dump()
    sessions = SqlImportSessionRepository(session)
    async with unit_of_work(session) as uow:
        sid = await sessions.create(
            user_id=__import__("uuid").UUID(user_id), source="pdf", parsed=parsed
        )
        await uow.commit()
    return {"session_id": str(sid), "parsed": parsed}


@router.post("/pdf/commit")
async def pdf_commit(
    user_id: CurrentUserId,
    session: SessionDep,
    body: CommitPdfBody,
) -> dict[str, Any]:
    from uuid import UUID

    from src.universe.interfaces.api.deps import (
        achievement_crud,
        certification_crud,
        education_crud,
        experience_crud,
        language_crud,
        project_crud,
        skill_crud,
    )

    sessions = SqlImportSessionRepository(session)
    sess = await sessions.get(UUID(user_id), UUID(body.session_id))
    if sess is None:
        raise HTTPException(status_code=404, detail="Import session not found")

    edu_uc = education_crud(session)
    exp_uc = experience_crud(session)
    skill_uc = skill_crud(session)
    lang_uc = language_crud(session)
    cert_uc = certification_crud(session)
    proj_uc = project_crud(session)
    ach_uc = achievement_crud(session)

    async with unit_of_work(session) as uow:
        summary = await commit_selection(
            user_id=user_id,
            parsed=sess["parsed"],
            selection=body.selection or {},
            edu_uc=edu_uc,
            exp_uc=exp_uc,
            skill_uc=skill_uc,
            lang_uc=lang_uc,
            cert_uc=cert_uc,
            project_uc=proj_uc,
            achievement_uc=ach_uc,
            uow=uow,
        )
        await sessions.mark_committed(UUID(body.session_id))
        await uow.commit()
    return {"committed": summary}
