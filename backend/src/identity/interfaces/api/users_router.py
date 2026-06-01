"""Users router: /api/v1/users/me/{...}"""
from __future__ import annotations

import io
import json
import zipfile
from dataclasses import asdict
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import Response, StreamingResponse

from src.identity.application.use_cases import (
    AdvanceOnboarding,
    ConfirmMfa,
    CurrentUserDto,
    DeleteAccount,
    DisableMfa,
    ExportUserData,
    GetCurrentUser,
    SetUserTier,
    SetupMfa,
)
from src.identity.infrastructure.photo_storage import (
    delete_avatar,
    load_avatar,
    save_avatar,
)
from src.identity.infrastructure.repositories import SqlAlchemyUserRepository
from src.identity.interfaces.api.deps import (
    CurrentUserId,
    SessionDep,
    delete_account_dep,
    export_user_data_dep,
    get_current_user_uc_dep,
)
from src.identity.interfaces.api.schemas import (
    CurrentUserResponse,
    GenericOkResponse,
    MfaCodeRequest,
    MfaSetupResponse,
    MfaStatusResponse,
    NotificationPrefsRequest,
    NotificationPrefsResponse,
    OnboardingAdvanceRequest,
    SetTierRequest,
)
from src.shared.uow import unit_of_work

router = APIRouter()


def _user_response(dto: CurrentUserDto) -> CurrentUserResponse:
    """Map the use-case DTO to the API response (identical field set)."""
    return CurrentUserResponse(**asdict(dto))


@router.get("/me", response_model=CurrentUserResponse)
async def me(
    user_id: CurrentUserId,
    uc: Annotated[GetCurrentUser, Depends(get_current_user_uc_dep)],
) -> CurrentUserResponse:
    result = await uc.execute(user_id=user_id)
    if result.is_failure:
        raise result.error  # type: ignore[union-attr]
    dto = result.value  # type: ignore[union-attr]
    return _user_response(dto)


@router.post("/me/tier", response_model=CurrentUserResponse)
async def set_tier(
    body: SetTierRequest,
    user_id: CurrentUserId,
    session: SessionDep,
) -> CurrentUserResponse:
    """Set the user's subscription tier.

    Dev/admin endpoint — in production this is driven by Stripe webhooks.
    Exposed in dev so we can flip free→pro without Stripe wired up.
    """
    from src.shared.config import get_settings

    # Self-serve tier change is a paid-feature bypass — only allow it outside
    # production, where tier is reconciled exclusively from Stripe webhooks.
    if get_settings().is_production:
        raise HTTPException(status_code=403, detail="tier_is_managed_by_billing")
    uc = SetUserTier(SqlAlchemyUserRepository(session))
    async with unit_of_work(session) as uow:
        result = await uc.execute(user_id=user_id, tier=body.tier, uow=uow)
        if result.is_failure:
            raise result.error  # type: ignore[union-attr]
        await uow.commit()
        dto = result.value  # type: ignore[union-attr]
    return _user_response(dto)


@router.post("/me/onboarding/advance", response_model=CurrentUserResponse)
async def advance_onboarding(
    body: OnboardingAdvanceRequest,
    user_id: CurrentUserId,
    session: SessionDep,
) -> CurrentUserResponse:
    """Advance server-side onboarding state: recompute activation from the
    user's real signals and, when ``complete`` is true, mark the wizard done.
    Idempotent; replaces the old localStorage 'onboarding done' flag."""
    uc = AdvanceOnboarding(SqlAlchemyUserRepository(session))
    async with unit_of_work(session) as uow:
        result = await uc.execute(user_id=user_id, complete=body.complete, uow=uow)
        if result.is_failure:
            raise result.error  # type: ignore[union-attr]
        await uow.commit()
        dto = result.value  # type: ignore[union-attr]
    return _user_response(dto)


@router.post("/me/mfa/setup", response_model=MfaSetupResponse)
async def mfa_setup(
    user_id: CurrentUserId,
    session: SessionDep,
) -> MfaSetupResponse:
    """Begin MFA enrolment — returns the secret + otpauth URI for the QR code.

    MFA isn't active until /me/mfa/confirm succeeds with a valid code.
    """
    uc = SetupMfa(SqlAlchemyUserRepository(session))
    result = await uc.execute(user_id=user_id)
    if result.is_failure:
        raise result.error  # type: ignore[union-attr]
    await session.commit()
    setup = result.value  # type: ignore[union-attr]
    return MfaSetupResponse(secret=setup.secret, otpauth_uri=setup.otpauth_uri)


@router.post("/me/mfa/confirm", response_model=MfaStatusResponse)
async def mfa_confirm(
    body: MfaCodeRequest,
    user_id: CurrentUserId,
    session: SessionDep,
) -> MfaStatusResponse:
    """Finish enrolment: verify a code against the pending secret + enable MFA."""
    uc = ConfirmMfa(SqlAlchemyUserRepository(session))
    result = await uc.execute(user_id=user_id, code=body.code)
    if result.is_failure:
        raise result.error  # type: ignore[union-attr]
    await session.commit()
    return MfaStatusResponse(mfa_enabled=True)


@router.post("/me/mfa/disable", response_model=MfaStatusResponse)
async def mfa_disable(
    body: MfaCodeRequest,
    user_id: CurrentUserId,
    session: SessionDep,
) -> MfaStatusResponse:
    """Disable MFA — requires a valid current TOTP code."""
    uc = DisableMfa(SqlAlchemyUserRepository(session))
    result = await uc.execute(user_id=user_id, code=body.code)
    if result.is_failure:
        raise result.error  # type: ignore[union-attr]
    await session.commit()
    return MfaStatusResponse(mfa_enabled=False)


@router.get("/me/notifications", response_model=NotificationPrefsResponse)
async def get_notification_prefs(
    user_id: CurrentUserId,
    session: SessionDep,
) -> NotificationPrefsResponse:
    """Read the user's notification opt-outs (currently the reminders digest)."""
    from src.identity.infrastructure.orm import UserOrm

    row = await session.get(UserOrm, UUID(user_id))
    if row is None:
        raise HTTPException(status_code=404, detail="not_found")
    return NotificationPrefsResponse(email_reminders=bool(row.notify_email_reminders))


@router.patch("/me/notifications", response_model=NotificationPrefsResponse)
async def set_notification_prefs(
    body: NotificationPrefsRequest,
    user_id: CurrentUserId,
    session: SessionDep,
) -> NotificationPrefsResponse:
    """Toggle the daily reminders digest email on/off for this user."""
    from src.identity.infrastructure.orm import UserOrm

    row = await session.get(UserOrm, UUID(user_id))
    if row is None:
        raise HTTPException(status_code=404, detail="not_found")
    row.notify_email_reminders = body.email_reminders
    await session.commit()
    return NotificationPrefsResponse(email_reminders=bool(row.notify_email_reminders))


@router.get("/me/export")
async def export_my_data(
    user_id: CurrentUserId,
    uc: Annotated[ExportUserData, Depends(export_user_data_dep)],
) -> StreamingResponse:
    result = await uc.execute(user_id=user_id)
    if result.is_failure:
        raise result.error  # type: ignore[union-attr]
    payload = result.value  # type: ignore[union-attr]
    readme = (
        "This archive contains every record we hold linked to your account, "
        "per GDPR Article 20 (data portability)."
    )
    # If any table failed to export, the payload carries an `errors` list — make
    # the gap explicit in the README so the archive is never presented as
    # complete when it isn't.
    failed = payload.get("errors") if isinstance(payload, dict) else None
    if failed:
        readme += (
            "\n\nNOTE: some categories could not be exported this time "
            f"({', '.join(failed)}). See the `errors` field in export.json and "
            "please request your export again, or contact support."
        )
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("export.json", json.dumps(payload, indent=2, default=str))
        zf.writestr("README.txt", readme)
    buf.seek(0)
    return StreamingResponse(
        buf,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="cvs-saas-export-{user_id}.zip"'},
    )


@router.delete("/me", response_model=GenericOkResponse)
async def delete_me(
    user_id: CurrentUserId,
    uc: Annotated[DeleteAccount, Depends(delete_account_dep)],
    session: SessionDep,
) -> GenericOkResponse:
    from src.agents.infrastructure.byok import delete_credential
    from src.integrations.infrastructure.repositories import (
        SqlExternalAccountRepository,
    )
    from src.mcp_server.infrastructure.oauth_store import OAuthStore

    async with unit_of_work(session) as uow:
        result = await uc.execute(user_id=user_id, uow=uow)
        if result.is_failure:
            raise result.error  # type: ignore[union-attr]
        # The use case soft-deletes + revokes browser refresh tokens. A
        # soft-delete does NOT fire the FK CASCADE, so anything holding a live
        # secret/token would otherwise outlive the "deleted" account. Clear them
        # all in phase 1: MCP OAuth tokens, the BYOK LLM key, and every external
        # account connection (GitHub/LinkedIn). Any failure raises before
        # commit, so the request never reports success on a partial erasure.
        await OAuthStore(session).revoke_all_for_user(UUID(user_id))
        await delete_credential(session, UUID(user_id))
        accounts = SqlExternalAccountRepository(session)
        for acc in await accounts.list_for_user(UUID(user_id)):
            await accounts.delete(UUID(user_id), acc.provider)
        await uow.commit()
    return GenericOkResponse()


@router.post("/me/photo")
async def upload_photo(
    user_id: CurrentUserId,
    session: SessionDep,
    file: UploadFile = File(...),
) -> dict[str, object]:
    raw = await file.read()
    try:
        info = await save_avatar(
            session,
            user_id=UUID(user_id),
            data=raw,
            mime=file.content_type,
            original_filename=file.filename,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    await session.commit()
    return info


@router.get("/me/photo")
async def get_photo(user_id: CurrentUserId, session: SessionDep) -> Response:
    result = await load_avatar(session, UUID(user_id))
    if result is None:
        # 204 (not 404) so a missing avatar isn't logged as a console error
        # by the browser; the client treats an empty body as "no photo".
        return Response(status_code=204)
    data, mime = result
    return Response(content=data, media_type=mime)


@router.delete("/me/photo", response_model=GenericOkResponse)
async def delete_photo(user_id: CurrentUserId, session: SessionDep) -> GenericOkResponse:
    removed = await delete_avatar(session, UUID(user_id))
    if removed:
        await session.commit()
    return GenericOkResponse()
