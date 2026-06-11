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
    CompleteMfaLogin,
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


async def pre_auth_session_dep() -> AsyncSession:
    """Session for the UNAUTHENTICATED identity flows.

    register/login/refresh/verify/reset/MFA ARE the trust boundary: they
    identify the user by credential or token-hash lookup and must write
    user-scoped rows (subscriptions, refresh_tokens, email_tokens) before any
    JWT — and therefore any RLS user context — exists. They run in the trusted
    service scope (policy bypass). Every authenticated surface keeps the
    per-user RLS context set by current_user_id(). Endpoints sharing this
    session MUST declare `PreAuthSessionDep` too, so FastAPI's dependency
    cache hands the use-case factories the same scoped session.
    """
    async for s in get_session():
        await set_rls_user(s, None)
        yield s


PreAuthSessionDep = Annotated[AsyncSession, Depends(pre_auth_session_dep)]


async def service_session_dep() -> AsyncSession:
    """Session for TRUSTED anonymous endpoints that legitimately operate across
    users without a JWT: Stripe webhooks (HMAC-verified) and capability-token
    resolvers (CV share links). The signature / unguessable token IS the
    authorization, so these run in the service scope (RLS bypass) exactly like
    background workers. Without arming RLS, FORCE RLS (migration 0039) denies
    every row: the webhook 500-loops and a paid plan never activates, and share
    links 404 on every valid token. This is the same fix already applied to
    pre-auth identity flows and the worker tasks."""
    async for s in get_session():
        await set_rls_user(s, None)
        yield s


ServiceSessionDep = Annotated[AsyncSession, Depends(service_session_dep)]


def register_user_dep(session: PreAuthSessionDep) -> RegisterUser:
    return RegisterUser(
        SqlAlchemyUserRepository(session),
        SqlAlchemyEmailTokenRepository(session),
        get_email_sender(),
    )


def create_trial_subscription_dep(session: PreAuthSessionDep) -> CreateTrialSubscription:
    return CreateTrialSubscription(SqlAlchemySubscriptionRepository(session))


def verify_email_dep(session: PreAuthSessionDep) -> VerifyEmail:
    async def _send_welcome(user_id: UUID) -> None:
        await enqueue_transactional_email(
            user_id=user_id, template="welcome", context=None
        )

    return VerifyEmail(
        SqlAlchemyUserRepository(session),
        SqlAlchemyEmailTokenRepository(session),
        welcome_emailer=_send_welcome,
    )


def login_dep(session: PreAuthSessionDep) -> Login:
    return Login(
        SqlAlchemyUserRepository(session),
        SqlAlchemyRefreshTokenRepository(session),
    )


def refresh_dep(session: PreAuthSessionDep) -> RefreshAccess:
    return RefreshAccess(
        SqlAlchemyUserRepository(session),
        SqlAlchemyRefreshTokenRepository(session),
    )


def complete_mfa_login_dep(session: PreAuthSessionDep) -> CompleteMfaLogin:
    return CompleteMfaLogin(
        SqlAlchemyUserRepository(session),
        SqlAlchemyRefreshTokenRepository(session),
    )


def request_password_reset_dep(session: PreAuthSessionDep) -> RequestPasswordReset:
    return RequestPasswordReset(
        SqlAlchemyUserRepository(session),
        SqlAlchemyEmailTokenRepository(session),
        get_email_sender(),
    )


def reset_password_dep(session: PreAuthSessionDep) -> ResetPassword:
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
    # is_paying (not is_pro) so a `premium` subscriber isn't denied paid features.
    if not user.is_paying:
        raise HTTPException(
            status_code=402,
            detail={
                "error": "tier_required",
                "required_tier": "pro",
                "current_tier": user.tier,
                "message": "Esta función requiere un plan de pago.",
            },
        )
    return user_id


ProUserId = Annotated[str, Depends(require_pro_tier)]


def get_request_meta(request: Request) -> dict[str, Any]:
    return {
        "user_agent": request.headers.get("user-agent"),
        "ip_address": (request.client.host if request.client else None),
    }
