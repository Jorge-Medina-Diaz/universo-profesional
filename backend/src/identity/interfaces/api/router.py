"""Auth router: /api/v1/auth/*"""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Request, status

from src.billing.application.use_cases import CreateTrialSubscription
from src.identity.application.use_cases import (
    CompleteMfaLogin,
    Login,
    RefreshAccess,
    RegisterUser,
    RequestPasswordReset,
    ResetPassword,
    VerifyEmail,
)
from src.identity.interfaces.api.deps import (
    PreAuthSessionDep,
    complete_mfa_login_dep,
    create_trial_subscription_dep,
    get_request_meta,
    login_dep,
    refresh_dep,
    register_user_dep,
    request_password_reset_dep,
    reset_password_dep,
    verify_email_dep,
)
from src.identity.interfaces.api.schemas import (
    GenericOkResponse,
    LoginRequest,
    MfaLoginRequest,
    PasswordResetConfirm,
    PasswordResetRequest,
    RefreshRequest,
    RegisterRequest,
    RegisterResponse,
    TokenResponse,
    VerifyEmailRequest,
)
from src.shared.config import get_settings
from src.shared.metrics import logins_total
from src.shared.rate_limit import limiter
from src.shared.security import utc_now
from src.shared.uow import unit_of_work

router = APIRouter()


@router.post("/register", response_model=RegisterResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("10/hour")
async def register(
    request: Request,
    body: RegisterRequest,
    uc: Annotated[RegisterUser, Depends(register_user_dep)],
    trial_uc: Annotated[CreateTrialSubscription, Depends(create_trial_subscription_dep)],
    session: PreAuthSessionDep,
) -> RegisterResponse:
    async with unit_of_work(session) as uow:
        result = await uc.execute(
            email=str(body.email),
            password=body.password,
            display_name=body.display_name,
            locale=body.locale,
            uow=uow,
        )
        if result.is_failure:
            assert result.is_failure
            raise result.error  # type: ignore[union-attr]
        payload = result.value  # type: ignore[union-attr]
        await trial_uc.execute(user_id=payload.user_id, now=utc_now())
        await uow.commit()

    settings = get_settings()
    return RegisterResponse(
        user_id=payload.user_id,
        email=payload.email,
        verification_link=payload.verification_link if settings.is_dev or settings.is_test else None,
    )


@router.post("/verify", response_model=GenericOkResponse)
async def verify_email(
    body: VerifyEmailRequest,
    uc: Annotated[VerifyEmail, Depends(verify_email_dep)],
    session: PreAuthSessionDep,
) -> GenericOkResponse:
    async with unit_of_work(session) as uow:
        result = await uc.execute(token=body.token, uow=uow)
        if result.is_failure:
            raise result.error  # type: ignore[union-attr]
        await uow.commit()
    return GenericOkResponse()


@router.post("/login", response_model=TokenResponse)
@limiter.limit("10/15minutes")
async def login(
    request: Request,
    body: LoginRequest,
    uc: Annotated[Login, Depends(login_dep)],
    session: PreAuthSessionDep,
) -> TokenResponse:
    meta = get_request_meta(request)
    async with unit_of_work(session) as uow:
        result = await uc.execute(
            email=str(body.email),
            password=body.password,
            user_agent=meta["user_agent"],
            ip_address=meta["ip_address"],
            uow=uow,
        )
        if result.is_failure:
            raise result.error  # type: ignore[union-attr]
        await uow.commit()
        tokens = result.value  # type: ignore[union-attr]
    if tokens.mfa_required:
        # Password OK but a second factor is required — no session yet.
        return TokenResponse(
            access_token="",
            refresh_token="",
            user_id=tokens.user_id,
            email=tokens.email,
            mfa_required=True,
            mfa_token=tokens.mfa_token,
        )
    logins_total.inc()
    return TokenResponse(
        access_token=tokens.access_token,
        refresh_token=tokens.refresh_token,
        user_id=tokens.user_id,
        email=tokens.email,
    )


@router.post("/mfa", response_model=TokenResponse)
@limiter.limit("10/15minutes")
async def mfa_login(
    request: Request,
    body: MfaLoginRequest,
    uc: Annotated[CompleteMfaLogin, Depends(complete_mfa_login_dep)],
    session: PreAuthSessionDep,
) -> TokenResponse:
    """Second step of an MFA login: exchange the mfa_token + TOTP code."""
    meta = get_request_meta(request)
    async with unit_of_work(session) as uow:
        result = await uc.execute(
            mfa_token=body.mfa_token,
            code=body.code,
            user_agent=meta["user_agent"],
            ip_address=meta["ip_address"],
            uow=uow,
        )
        if result.is_failure:
            raise result.error  # type: ignore[union-attr]
        await uow.commit()
        tokens = result.value  # type: ignore[union-attr]
    logins_total.inc()
    return TokenResponse(
        access_token=tokens.access_token,
        refresh_token=tokens.refresh_token,
        user_id=tokens.user_id,
        email=tokens.email,
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh(
    body: RefreshRequest,
    request: Request,
    uc: Annotated[RefreshAccess, Depends(refresh_dep)],
    session: PreAuthSessionDep,
) -> TokenResponse:
    meta = get_request_meta(request)
    async with unit_of_work(session) as uow:
        result = await uc.execute(
            refresh_token=body.refresh_token,
            user_agent=meta["user_agent"],
            ip_address=meta["ip_address"],
        )
        if result.is_failure:
            raise result.error  # type: ignore[union-attr]
        await uow.commit()
        tokens = result.value  # type: ignore[union-attr]
    return TokenResponse(
        access_token=tokens.access_token,
        refresh_token=tokens.refresh_token,
        user_id=tokens.user_id,
        email=tokens.email,
    )


@router.post("/password-reset", response_model=GenericOkResponse)
@limiter.limit("3/hour")
async def password_reset_request(
    request: Request,
    body: PasswordResetRequest,
    uc: Annotated[RequestPasswordReset, Depends(request_password_reset_dep)],
    session: PreAuthSessionDep,
) -> GenericOkResponse:
    async with unit_of_work(session) as uow:
        await uc.execute(email=str(body.email), uow=uow)
        await uow.commit()
    return GenericOkResponse()


@router.post("/password-reset/confirm", response_model=GenericOkResponse)
async def password_reset_confirm(
    body: PasswordResetConfirm,
    uc: Annotated[ResetPassword, Depends(reset_password_dep)],
    session: PreAuthSessionDep,
) -> GenericOkResponse:
    async with unit_of_work(session) as uow:
        result = await uc.execute(token=body.token, new_password=body.new_password, uow=uow)
        if result.is_failure:
            raise result.error  # type: ignore[union-attr]
        await uow.commit()
    return GenericOkResponse()
