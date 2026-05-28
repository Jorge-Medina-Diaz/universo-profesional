"""FastAPI dependencies for Identity endpoints + the shared `current_user` dep."""
from __future__ import annotations

from typing import Annotated, Any
from uuid import UUID

from fastapi import Depends, Header, Request
from jose import JWTError
from sqlalchemy.ext.asyncio import AsyncSession

from src.billing.application.use_cases import CreateTrialSubscription
from src.billing.infrastructure.repositories import SqlAlchemySubscriptionRepository
from src.identity.application.use_cases import (
    DeleteAccount,
    ExportUserData,
    GetCurrentUser,
    Login,
    RefreshAccess,
    RegisterUser,
    RequestPasswordReset,
    ResetPassword,
    VerifyEmail,
)
from src.identity.infrastructure.email_sender import get_email_sender
from src.identity.infrastructure.exporter import SqlUserDataExporter
from src.identity.infrastructure.repositories import (
    SqlAlchemyEmailTokenRepository,
    SqlAlchemyRefreshTokenRepository,
    SqlAlchemyUserRepository,
)
from src.identity.infrastructure.tasks import enqueue_transactional_email
from src.shared.db import get_session, set_rls_user
from src.shared.errors import UnauthorizedError
from src.shared.security import decode_jwt


async def session_dep() -> AsyncSession:
    """Wrapper so FastAPI sees a proper dependency function."""
    async for s in get_session():
        yield s


SessionDep = Annotated[AsyncSession, Depends(session_dep)]


def register_user_dep(session: SessionDep) -> RegisterUser:
    return RegisterUser(
        SqlAlchemyUserRepository(session),
        SqlAlchemyEmailTokenRepository(session),
        get_email_sender(),
    )


def create_trial_subscription_dep(session: SessionDep) -> CreateTrialSubscription:
    return CreateTrialSubscription(SqlAlchemySubscriptionRepository(session))


def verify_email_dep(session: SessionDep) -> VerifyEmail:
    async def _send_welcome(user_id: UUID) -> None:
        await enqueue_transactional_email(
            user_id=user_id, template="welcome", context=None
        )

    return VerifyEmail(
        SqlAlchemyUserRepository(session),
        SqlAlchemyEmailTokenRepository(session),
        welcome_emailer=_send_welcome,
    )


def login_dep(session: SessionDep) -> Login:
    return Login(
        SqlAlchemyUserRepository(session),
        SqlAlchemyRefreshTokenRepository(session),
    )


def refresh_dep(session: SessionDep) -> RefreshAccess:
    return RefreshAccess(
        SqlAlchemyUserRepository(session),
        SqlAlchemyRefreshTokenRepository(session),
    )


def request_password_reset_dep(session: SessionDep) -> RequestPasswordReset:
    return RequestPasswordReset(
        SqlAlchemyUserRepository(session),
        SqlAlchemyEmailTokenRepository(session),
        get_email_sender(),
    )


def reset_password_dep(session: SessionDep) -> ResetPassword:
    return ResetPassword(
        SqlAlchemyUserRepository(session),
        SqlAlchemyEmailTokenRepository(session),
        SqlAlchemyRefreshTokenRepository(session),
    )


def delete_account_dep(session: SessionDep) -> DeleteAccount:
    return DeleteAccount(
        SqlAlchemyUserRepository(session),
        SqlAlchemyRefreshTokenRepository(session),
    )


def export_user_data_dep(session: SessionDep) -> ExportUserData:
    return ExportUserData(SqlUserDataExporter(session))


def get_current_user_uc_dep(session: SessionDep) -> GetCurrentUser:
    return GetCurrentUser(SqlAlchemyUserRepository(session))


# --- Auth middleware-ish ---------------------------------------------------


async def current_user_id(
    authorization: Annotated[str | None, Header()] = None,
    session: SessionDep = None,  # type: ignore[assignment]
) -> str:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise UnauthorizedError("Missing bearer token")
    token = authorization.split(" ", 1)[1].strip()
    try:
        claims = decode_jwt(token, audience="cvs-saas-api")
    except JWTError as exc:
        raise UnauthorizedError(f"Invalid token: {exc}") from exc
    uid = claims.get("sub")
    if not uid:
        raise UnauthorizedError("Token missing sub")
    # Set RLS context for the rest of the request lifecycle
    from uuid import UUID

    await set_rls_user(session, UUID(uid))
    return str(uid)


CurrentUserId = Annotated[str, Depends(current_user_id)]


async def require_pro_tier(
    user_id: CurrentUserId,
    session: SessionDep,
) -> str:
    """Guard endpoint behind tier='pro'.

    Returns the user_id (so endpoints can use it directly) or raises 402.
    402 Payment Required is the semantically correct status for "this works
    but you need to upgrade" — clients can intercept it to show the paywall.
    """
    from uuid import UUID

    from fastapi import HTTPException

    repo = SqlAlchemyUserRepository(session)
    user = await repo.get_by_id(UUID(user_id))
    if user is None:
        raise UnauthorizedError("User not found")
    if not user.is_pro:
        raise HTTPException(
            status_code=402,
            detail={
                "error": "tier_required",
                "required_tier": "pro",
                "current_tier": user.tier,
                "message": "Esta función requiere el plan PRO.",
            },
        )
    return user_id


ProUserId = Annotated[str, Depends(require_pro_tier)]


def get_request_meta(request: Request) -> dict[str, Any]:
    return {
        "user_agent": request.headers.get("user-agent"),
        "ip_address": (request.client.host if request.client else None),
    }
