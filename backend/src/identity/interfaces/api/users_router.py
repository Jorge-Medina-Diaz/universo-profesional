"""Users router: /api/v1/users/me/{...}"""
from __future__ import annotations

import io
import json
import zipfile
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import Response, StreamingResponse

from src.identity.application.use_cases import (
    DeleteAccount,
    ExportUserData,
    GetCurrentUser,
    SetUserTier,
)
from src.identity.infrastructure.repositories import SqlAlchemyUserRepository
from src.identity.infrastructure.photo_storage import (
    delete_avatar,
    load_avatar,
    save_avatar,
)
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
    SetTierRequest,
)
from src.shared.uow import unit_of_work

router = APIRouter()


@router.get("/me", response_model=CurrentUserResponse)
async def me(
    user_id: CurrentUserId,
    uc: Annotated[GetCurrentUser, Depends(get_current_user_uc_dep)],
) -> CurrentUserResponse:
    result = await uc.execute(user_id=user_id)
    if result.is_failure:
        raise result.error  # type: ignore[union-attr]
    dto = result.value  # type: ignore[union-attr]
    return CurrentUserResponse(
        user_id=dto.user_id,
        email=dto.email,
        display_name=dto.display_name,
        locale=dto.locale,
        email_verified=dto.email_verified,
        mfa_enabled=dto.mfa_enabled,
        created_at=dto.created_at,
        tier=dto.tier,
        tier_updated_at=dto.tier_updated_at,
    )


@router.post("/me/tier", response_model=CurrentUserResponse)
async def set_tier(
    body: SetTierRequest,
    user_id: CurrentUserId,
    session: SessionDep,
) -> CurrentUserResponse:
    """Set the user's subscription tier.

    Dev/admin endpoint — in production this is driven by Stripe webhooks.
    Exposed today so we can flip free→pro without Stripe wired up.
    """
    uc = SetUserTier(SqlAlchemyUserRepository(session))
    async with unit_of_work(session) as uow:
        result = await uc.execute(user_id=user_id, tier=body.tier, uow=uow)
        if result.is_failure:
            raise result.error  # type: ignore[union-attr]
        await uow.commit()
        dto = result.value  # type: ignore[union-attr]
    return CurrentUserResponse(
        user_id=dto.user_id,
        email=dto.email,
        display_name=dto.display_name,
        locale=dto.locale,
        email_verified=dto.email_verified,
        mfa_enabled=dto.mfa_enabled,
        created_at=dto.created_at,
        tier=dto.tier,
        tier_updated_at=dto.tier_updated_at,
    )


@router.get("/me/export")
async def export_my_data(
    user_id: CurrentUserId,
    uc: Annotated[ExportUserData, Depends(export_user_data_dep)],
) -> StreamingResponse:
    result = await uc.execute(user_id=user_id)
    if result.is_failure:
        raise result.error  # type: ignore[union-attr]
    payload = result.value  # type: ignore[union-attr]
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("export.json", json.dumps(payload, indent=2, default=str))
        zf.writestr(
            "README.txt",
            "This archive contains every record we hold linked to your account, "
            "per GDPR Article 20 (data portability).",
        )
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
    async with unit_of_work(session) as uow:
        result = await uc.execute(user_id=user_id, uow=uow)
        if result.is_failure:
            raise result.error  # type: ignore[union-attr]
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
