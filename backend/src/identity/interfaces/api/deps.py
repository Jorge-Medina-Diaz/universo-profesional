"""FastAPI dependencies for Identity endpoints + the shared `current_user` dep."""
from __future__ import annotations

from typing import Annotated, Any

from fastapi import Depends, Header, Request
from jose import JWTError
from sqlalchemy.ext.asyncio import AsyncSession

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
from src.identity.infrastructure.email_sender import MockEmailSender
from src.identity.infrastructure.exporter import SqlUserDataExporter
from src.identity.infrastructure.repositories import (
    SqlAlchemyEmailTokenRepository,
    SqlAlchemyRefreshTokenRepository,
    SqlAlchemyUserRepository,
)
from src.shared.db import get_session, set_rls_user
from src.shared.errors import UnauthorizedError
from src.shared.security import decode_jwt


async def session_dep() -> AsyncSession:  # type: ignore[return-value]
    """Wrapper so FastAPI sees a proper dependency function."""
    async for s in get_session():
        yield s  # type: ignore[misc]


SessionDep = Annotated[AsyncSession, Depends(session_dep)]


def register_user_dep(session: SessionDep) -> RegisterUser:
    return RegisterUser(
        SqlAlchemyUserRepository(session),
        SqlAlchemyEmailTokenRepository(session),
        MockEmailSender(),
    )


def verify_email_dep(session: SessionDep) -> VerifyEmail:
    return VerifyEmail(
        SqlAlchemyUserRepository(session),
        SqlAlchemyEmailTokenRepository(session),
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
        MockEmailSender(),
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


def get_request_meta(request: Request) -> dict[str, Any]:
    return {
        "user_agent": request.headers.get("user-agent"),
        "ip_address": (request.client.host if request.client else None),
    }
