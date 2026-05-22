"""/api/v1/integrations/* — GitHub OAuth + sync, LinkedIn (OIDC/DMA/Bright Data/ZIP), PDF CV import."""
from __future__ import annotations

import urllib.parse
from datetime import timedelta
from typing import Annotated, Any
from uuid import UUID, uuid4

from fastapi import APIRouter, Body, Depends, File, HTTPException, UploadFile
from fastapi.responses import RedirectResponse
from pydantic import BaseModel

from src.identity.interfaces.api.deps import CurrentUserId, ProUserId, SessionDep
from src.integrations.application.connect_disconnect import (
    ConnectGithub,
    DisconnectAccount,
    ListConnections,
)
from src.integrations.application.github_sync import SyncGithub
from src.integrations.application.linkedin_brightdata_sync import (
    BrightDataLinkedInProvider,
)
from src.integrations.application.linkedin_csv_deep import (
    commit_parsed,
    parse_linkedin_zip,
)
from src.integrations.application.linkedin_dma_sync import DmaLinkedInProvider
from src.integrations.application.linkedin_mapper import profile_to_universe_payloads
from src.integrations.application.linkedin_oidc import issue_state, parse_state
from src.integrations.application.linkedin_sync import (
    SyncLinkedinBrightdata,
    SyncLinkedinDma,
)
from src.integrations.application.pdf_cv_parser import (
    ParsedCv,
    commit_selection,
    parse_cv_pdf,
)
from src.integrations.domain.external_account import (
    ExternalAccount,
    IntegrationConnected,
)
from src.integrations.infrastructure.linkedin_brightdata_client import BrightDataError
from src.integrations.infrastructure.linkedin_dma_client import (
    build_dma_authorize_url,
    exchange_dma_code_for_token,
)
from src.integrations.infrastructure.repositories import (
    SqlExternalAccountRepository,
    SqlImportSessionRepository,
    SqlSyncRunsRepository,
)
from src.shared.config import get_settings
from src.shared.errors import ValidationError
from src.shared.security import utc_now
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


@router.post("/github/sync-async")
async def github_sync_async(user_id: CurrentUserId) -> dict[str, Any]:
    """Enqueue the GitHub sync on the Arq worker and return immediately.

    The user sees progress through the existing `/sync-runs` polling +
    `<SyncTaskTray>` widget. When Redis is unavailable we transparently
    fall back to running the sync inline (see `queue.enqueue_integration_task`).
    """
    from src.integrations.infrastructure.queue import enqueue_integration_task

    res = await enqueue_integration_task("run_github_sync_task", user_id=user_id)
    return res


@router.post("/linkedin/dma/sync-async")
async def linkedin_dma_sync_async(user_id: CurrentUserId) -> dict[str, Any]:
    from src.integrations.infrastructure.queue import enqueue_integration_task

    return await enqueue_integration_task(
        "run_linkedin_dma_sync_task", user_id=user_id
    )


class _BrightDataAsyncBody(BaseModel):
    linkedin_url: str | None = None
    fresh: bool = False


@router.post("/linkedin/brightdata/sync-async")
async def linkedin_brightdata_sync_async(
    user_id: CurrentUserId, body: _BrightDataAsyncBody = Body(default=_BrightDataAsyncBody())
) -> dict[str, Any]:
    from src.integrations.infrastructure.queue import enqueue_integration_task

    return await enqueue_integration_task(
        "run_linkedin_brightdata_sync_task",
        user_id=user_id,
        linkedin_url=body.linkedin_url,
        fresh=body.fresh,
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


@router.post("/sync-runs/{run_id}/cancel")
async def cancel_sync_run(
    run_id: str, user_id: CurrentUserId, session: SessionDep
) -> dict[str, Any]:
    """Soft-cancel a sync run.

    Marks `summary._cancelled_requested_at` so the row is filtered out of
    `list_for_user`. Sprint F caveat: the worker doing the sync does NOT
    poll this flag yet — the request is honoured at the UI level only.
    Future iterations will let the actual sync abort mid-flight.
    """
    import uuid as _uuid

    runs = SqlSyncRunsRepository(session)
    try:
        rid = _uuid.UUID(run_id)
    except ValueError:
        return {"ok": False, "error": "invalid_id"}
    ok = await runs.request_cancel(rid, _uuid.UUID(user_id))
    if not ok:
        return {"ok": False, "error": "not_found"}
    await session.commit()
    return {"ok": True}


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


_MAX_PDF_UPLOAD_BYTES = 50 * 1024 * 1024  # 50 MB hard cap (zip-bomb guard)


@router.post("/pdf/parse")
async def pdf_parse(
    user_id: CurrentUserId,
    session: SessionDep,
    file: UploadFile = File(...),
) -> dict[str, Any]:
    contents = await file.read()
    if len(contents) > _MAX_PDF_UPLOAD_BYTES:
        raise HTTPException(
            status_code=413,
            detail=(
                f"PDF exceeds {_MAX_PDF_UPLOAD_BYTES // (1024 * 1024)} MB limit "
                f"(got {len(contents) // (1024 * 1024)} MB)"
            ),
        )
    if not contents.startswith(b"%PDF"):
        raise HTTPException(status_code=400, detail="file is not a valid PDF")
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


# ---------- LinkedIn capabilities (probe) ---------- #


@router.get("/linkedin/status")
async def linkedin_status() -> dict[str, Any]:
    """Tell the frontend which LinkedIn paths actually work right now.

    Each path can be either real (talks to LinkedIn / Bright Data) or a mock
    fixture. We surface this so the UI can label the buttons honestly —
    nothing is worse than thinking you've imported your real profile when
    you've just pulled canned demo data.
    """
    s = get_settings()
    return {
        "oidc": {
            "configured": bool(s.linkedin_client_id and s.linkedin_client_secret),
        },
        "dma": {
            "configured": bool(s.linkedin_client_id and s.linkedin_client_secret),
            "enabled": s.linkedin_dma_enabled,
            "uses_fixture": not (
                s.linkedin_client_id and s.linkedin_client_secret and s.linkedin_dma_enabled
            ),
        },
        "brightdata": {
            "configured": bool(s.brightdata_api_key),
            "uses_fixture": not bool(s.brightdata_api_key),
        },
        "zip": {
            "configured": True,  # ZIP always works — it's just a file upload
            "uses_fixture": False,
        },
    }


# ---------- LinkedIn DMA (official 3rd-party API, EEA-only) ---------- #


def _dma_redirect_uri() -> str:
    s = get_settings()
    return f"{s.canonical_base_url}/api/v1/integrations/linkedin/dma/callback"


@router.get("/linkedin/dma/authorize")
async def linkedin_dma_authorize(user_id: CurrentUserId) -> dict[str, str]:
    """Return the LinkedIn authorize URL with the DMA portability scope.

    Distinct from the OIDC sign-in flow because DMA needs an extra scope
    (`r_dma_portability_3rd_party`) that LinkedIn only grants on apps
    approved for the EU Digital Markets Act compliance program. We always
    return a URL (so the frontend renders the button) plus a `dma_enabled`
    flag the UI uses to show "in waiting list" when the flag is off.
    """
    s = get_settings()
    if not s.linkedin_client_id:
        # No client configured — give the frontend a sentinel URL so it falls
        # back to the "Probar con datos de muestra" path without a 503.
        return {
            "authorize_url": f"{s.frontend_base_url}/#/connections?error=linkedin_not_configured",
            "dma_enabled": "false",
        }
    state = issue_state(link_user_id=user_id)
    url = build_dma_authorize_url(
        client_id=s.linkedin_client_id,
        redirect_uri=_dma_redirect_uri(),
        state=state,
    )
    return {"authorize_url": url, "dma_enabled": str(s.linkedin_dma_enabled).lower()}


@router.get("/linkedin/dma/callback")
async def linkedin_dma_callback(
    session: SessionDep,
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
    error_description: str | None = None,
) -> RedirectResponse:
    s = get_settings()
    if error:
        return RedirectResponse(
            url=f"{s.frontend_base_url}/#/connections?error={urllib.parse.quote(error)}",
            status_code=302,
        )
    if not code or not state:
        raise HTTPException(status_code=400, detail="Missing code or state")
    try:
        parsed_state = parse_state(state)
    except ValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    user_id = parsed_state.get("link_user_id")
    if not user_id:
        raise HTTPException(status_code=400, detail="DMA flow requires an authed user")

    token_bundle = await exchange_dma_code_for_token(
        client_id=s.linkedin_client_id or "",
        client_secret=s.linkedin_client_secret or "",
        code=code,
        redirect_uri=_dma_redirect_uri(),
    )
    access_token = token_bundle["access_token"]
    expires_in = int(token_bundle.get("expires_in") or 60 * 60 * 24 * 60)

    accounts = SqlExternalAccountRepository(session)
    async with unit_of_work(session) as uow:
        account = ExternalAccount.create(
            user_id=UUID(user_id),
            provider="linkedin_dma",
            provider_user_id=None,
            provider_username=None,
            access_token=access_token,
            refresh_token=token_bundle.get("refresh_token"),
            expires_at=utc_now() + timedelta(seconds=expires_in),
            scopes=(token_bundle.get("scope", "").split(" ") if token_bundle.get("scope") else []),
            metadata={},
            now=utc_now(),
        )
        await accounts.upsert(account)
        uow.add_event(
            IntegrationConnected(user_id=UUID(user_id), provider="linkedin_dma")
        )
        await uow.commit()

    return RedirectResponse(
        url=f"{s.frontend_base_url}/#/connections?connected=linkedin_dma",
        status_code=302,
    )


@router.post("/linkedin/dma/sync")
async def linkedin_dma_sync(
    user_id: CurrentUserId, session: SessionDep
) -> dict[str, Any]:
    """Fetch the DMA snapshot and open an import session for review."""
    accounts = SqlExternalAccountRepository(session)
    sessions = SqlImportSessionRepository(session)
    runs = SqlSyncRunsRepository(session)
    uc = SyncLinkedinDma(accounts, sessions, runs)
    async with unit_of_work(session) as uow:
        result = await uc.execute(user_id=user_id, uow=uow)
        await uow.commit()
    return result


@router.post("/linkedin/dma/commit")
async def linkedin_dma_commit(
    user_id: CurrentUserId,
    session: SessionDep,
    body: dict[str, Any],
) -> dict[str, Any]:
    """Commit a previously created DMA import session selectively.

    Body: { session_id, selection?: {section: [indices]} }
    """
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
    sid = body.get("session_id")
    if not sid:
        raise HTTPException(status_code=400, detail="session_id is required")
    sess = await sessions.get(UUID(user_id), UUID(sid))
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

    selection = body.get("selection")
    async with unit_of_work(session) as uow:
        if selection:
            summary = await commit_selection(
                user_id=user_id,
                parsed=sess["parsed"],
                selection=selection,
                edu_uc=edu_uc,
                exp_uc=exp_uc,
                skill_uc=skill_uc,
                lang_uc=lang_uc,
                cert_uc=cert_uc,
                project_uc=proj_uc,
                achievement_uc=ach_uc,
                uow=uow,
            )
        else:
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
        await sessions.mark_committed(UUID(sid))
        await uow.commit()
    return {"committed": summary}


@router.delete("/linkedin/dma")
async def linkedin_dma_disconnect(
    user_id: CurrentUserId, session: SessionDep
) -> dict[str, bool]:
    uc = DisconnectAccount(SqlExternalAccountRepository(session))
    async with unit_of_work(session) as uow:
        r = await uc.execute(user_id=user_id, provider="linkedin_dma", uow=uow)
        if r.is_failure:
            raise r.error  # type: ignore[union-attr]
        await uow.commit()
    return {"ok": True}


# ---------- LinkedIn Bright Data (PRO tier) ---------- #


class BrightdataSyncBody(BaseModel):
    linkedin_url: str | None = None
    fresh: bool = False


@router.post("/linkedin/brightdata/sync")
async def linkedin_brightdata_sync(
    user_id: ProUserId,
    session: SessionDep,
    body: BrightdataSyncBody,
) -> dict[str, Any]:
    """Pull profile via Bright Data. Gated behind tier='pro' (402 otherwise).

    The user can supply a public LinkedIn URL; if not, we resolve from the
    OIDC account metadata. Returns an import_session with the parsed payload
    so the frontend can present a confirm-screen identical to ZIP/PDF.
    """
    accounts = SqlExternalAccountRepository(session)
    sessions = SqlImportSessionRepository(session)
    runs = SqlSyncRunsRepository(session)
    uc = SyncLinkedinBrightdata(accounts, sessions, runs)
    async with unit_of_work(session) as uow:
        try:
            result = await uc.execute(
                user_id=user_id,
                linkedin_url=body.linkedin_url,
                fresh=body.fresh,
                uow=uow,
            )
        except BrightDataError as exc:
            raise HTTPException(
                status_code=502,
                detail={
                    "error": "brightdata_failed",
                    "upstream_status": exc.status,
                    "detail": exc.detail,
                },
            ) from exc
        await uow.commit()
    return result


@router.post("/linkedin/brightdata/commit")
async def linkedin_brightdata_commit(
    user_id: ProUserId,
    session: SessionDep,
    body: dict[str, Any],
) -> dict[str, Any]:
    """Commit a Bright Data import session — same shape as DMA/ZIP/PDF commit."""
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
    sid = body.get("session_id")
    if not sid:
        raise HTTPException(status_code=400, detail="session_id is required")
    sess = await sessions.get(UUID(user_id), UUID(sid))
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

    selection = body.get("selection")
    async with unit_of_work(session) as uow:
        if selection:
            summary = await commit_selection(
                user_id=user_id,
                parsed=sess["parsed"],
                selection=selection,
                edu_uc=edu_uc,
                exp_uc=exp_uc,
                skill_uc=skill_uc,
                lang_uc=lang_uc,
                cert_uc=cert_uc,
                project_uc=proj_uc,
                achievement_uc=ach_uc,
                uow=uow,
            )
        else:
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
        await sessions.mark_committed(UUID(sid))
        await uow.commit()
    return {"committed": summary}
