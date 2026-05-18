"""Users router: /api/v1/users/me/{...}"""
from __future__ import annotations

import io
import json
import zipfile
from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from src.identity.application.use_cases import (
    DeleteAccount,
    ExportUserData,
    GetCurrentUser,
)
from src.identity.interfaces.api.deps import (
    CurrentUserId,
    SessionDep,
    delete_account_dep,
    export_user_data_dep,
    get_current_user_uc_dep,
)
from src.identity.interfaces.api.schemas import CurrentUserResponse, GenericOkResponse
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
