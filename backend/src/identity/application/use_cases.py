"""Identity use cases — pure application logic over ports.

Each use case is a callable class with an `execute()` method returning a
Result. Mapping to HTTP / MCP happens in the interfaces layer.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from src.identity.application.ports import (
    EmailSender,
    EmailTokenRepository,
    RefreshTokenRepository,
    UserDataExporter,
    UserRepository,
)
from src.identity.domain.user import User
from src.shared.config import get_settings
from src.shared.errors import (
    ConflictError,
    NotFoundError,
    UnauthorizedError,
    ValidationError,
)
from src.shared.result import Failure, Result, Success, err, ok
from src.shared.security import (
    encode_jwt,
    generate_token,
    hash_password,
    hash_token,
    utc_in,
    utc_now,
    verify_password,
)
from src.shared.uow import UnitOfWork
from src.shared.value_objects import Email


@dataclass(frozen=True)
class RegisteredUser:
    user_id: str
    email: str
    verification_link: str  # Returned for tests; in prod the email handler also sends it


# --- RegisterUser ----------------------------------------------------------


class RegisterUser:
    def __init__(
        self,
        users: UserRepository,
        email_tokens: EmailTokenRepository,
        emailer: EmailSender,
    ) -> None:
        self._users = users
        self._email_tokens = email_tokens
        self._emailer = emailer

    async def execute(
        self,
        *,
        email: str,
        password: str,
        display_name: str | None,
        locale: str,
        uow: UnitOfWork,
    ) -> Result[RegisteredUser, ConflictError | ValidationError]:
        if len(password) < 10:
            return err(ValidationError("Password must be at least 10 characters"))

        email_vo = Email.parse(email)
        existing = await self._users.get_by_email(str(email_vo))
        if existing is not None and not existing.is_deleted:
            return err(ConflictError("Email already registered"))

        password_hash = hash_password(password)
        now = utc_now()
        user = User.register(
            email=email_vo,
            password_hash=password_hash,
            display_name=display_name,
            locale=locale,
            now=now,
        )
        await self._users.save(user)

        # Email verification token (24h, single use)
        token = generate_token()
        token_h = hash_token(token)
        await self._email_tokens.create(
            user_id=user.id,
            token_hash=token_h,
            purpose="verify_email",
            expires_at=utc_in(hours=24),
        )

        settings = get_settings()
        link = f"{settings.frontend_base_url}/auth/verify?token={token}"
        await self._emailer.send_verification(to=str(user.email), link=link, locale=locale)

        uow.add_events(user.pop_events())
        return ok(
            RegisteredUser(
                user_id=str(user.id),
                email=str(user.email),
                verification_link=link,
            )
        )


# --- VerifyEmail -----------------------------------------------------------


class VerifyEmail:
    def __init__(
        self,
        users: UserRepository,
        email_tokens: EmailTokenRepository,
    ) -> None:
        self._users = users
        self._email_tokens = email_tokens

    async def execute(
        self, *, token: str, uow: UnitOfWork
    ) -> Result[bool, NotFoundError | ValidationError]:
        token_h = hash_token(token)
        now = utc_now()
        user_id = await self._email_tokens.consume(
            token_hash=token_h, purpose="verify_email", now=now
        )
        if user_id is None:
            return err(ValidationError("Invalid or expired verification token"))
        user = await self._users.get_by_id(user_id)
        if user is None:
            return err(NotFoundError("User no longer exists"))
        user.mark_verified(now=now)
        await self._users.save(user)
        uow.add_events(user.pop_events())
        return ok(True)


# --- Login -----------------------------------------------------------------


@dataclass(frozen=True)
class LoginTokens:
    access_token: str
    refresh_token: str
    user_id: str
    email: str


class Login:
    def __init__(
        self,
        users: UserRepository,
        refresh_tokens: RefreshTokenRepository,
    ) -> None:
        self._users = users
        self._refresh_tokens = refresh_tokens

    async def execute(
        self,
        *,
        email: str,
        password: str,
        user_agent: str | None,
        ip_address: str | None,
        uow: UnitOfWork,
    ) -> Result[LoginTokens, UnauthorizedError]:
        email_vo = Email.parse(email)
        user = await self._users.get_by_email(str(email_vo))
        if user is None or user.is_deleted or user.password_hash is None:
            return err(UnauthorizedError("Invalid credentials"))
        if not verify_password(password, user.password_hash):
            return err(UnauthorizedError("Invalid credentials"))
        if not user.is_verified:
            return err(UnauthorizedError("Email not verified"))

        now = utc_now()
        user.record_login(now=now)
        await self._users.save(user)

        settings = get_settings()
        access = encode_jwt(
            {
                "sub": str(user.id),
                "email": str(user.email),
                "iss": settings.canonical_base_url,
                "aud": "cvs-saas-api",
                "iat": int(now.timestamp()),
                "exp": int(utc_in(minutes=settings.jwt_access_ttl_minutes).timestamp()),
                "scope": "user",
            }
        )
        refresh = generate_token(48)
        refresh_h = hash_token(refresh)
        refresh_exp = utc_in(days=settings.jwt_refresh_ttl_days)
        await self._refresh_tokens.store(
            user_id=user.id,
            token_hash=refresh_h,
            expires_at=refresh_exp,
            user_agent=user_agent,
            ip_address=ip_address,
        )
        uow.add_events(user.pop_events())
        return ok(
            LoginTokens(
                access_token=access,
                refresh_token=refresh,
                user_id=str(user.id),
                email=str(user.email),
            )
        )


# --- RefreshAccess ---------------------------------------------------------


class RefreshAccess:
    def __init__(
        self,
        users: UserRepository,
        refresh_tokens: RefreshTokenRepository,
    ) -> None:
        self._users = users
        self._refresh_tokens = refresh_tokens

    async def execute(
        self,
        *,
        refresh_token: str,
        user_agent: str | None,
        ip_address: str | None,
    ) -> Result[LoginTokens, UnauthorizedError]:
        old_h = hash_token(refresh_token)
        new = generate_token(48)
        new_h = hash_token(new)
        settings = get_settings()
        new_exp = utc_in(days=settings.jwt_refresh_ttl_days)
        user_id = await self._refresh_tokens.rotate(
            old_token_hash=old_h,
            new_token_hash=new_h,
            new_expires_at=new_exp,
            user_agent=user_agent,
            ip_address=ip_address,
        )
        if user_id is None:
            return err(UnauthorizedError("Invalid or revoked refresh token"))
        user = await self._users.get_by_id(user_id)
        if user is None or user.is_deleted:
            return err(UnauthorizedError("User no longer exists"))

        now = utc_now()
        access = encode_jwt(
            {
                "sub": str(user.id),
                "email": str(user.email),
                "iss": settings.canonical_base_url,
                "aud": "cvs-saas-api",
                "iat": int(now.timestamp()),
                "exp": int(utc_in(minutes=settings.jwt_access_ttl_minutes).timestamp()),
                "scope": "user",
            }
        )
        return ok(
            LoginTokens(
                access_token=access,
                refresh_token=new,
                user_id=str(user.id),
                email=str(user.email),
            )
        )


# --- RequestPasswordReset --------------------------------------------------


class RequestPasswordReset:
    def __init__(
        self,
        users: UserRepository,
        email_tokens: EmailTokenRepository,
        emailer: EmailSender,
    ) -> None:
        self._users = users
        self._email_tokens = email_tokens
        self._emailer = emailer

    async def execute(self, *, email: str, uow: UnitOfWork) -> Result[bool, ValidationError]:
        # Always return success (don't leak whether email exists)
        try:
            email_vo = Email.parse(email)
        except ValidationError:
            return ok(True)
        user = await self._users.get_by_email(str(email_vo))
        if user is None or user.is_deleted:
            return ok(True)
        token = generate_token()
        token_h = hash_token(token)
        await self._email_tokens.create(
            user_id=user.id,
            token_hash=token_h,
            purpose="password_reset",
            expires_at=utc_in(minutes=15),
        )
        settings = get_settings()
        link = f"{settings.frontend_base_url}/auth/reset?token={token}"
        await self._emailer.send_password_reset(
            to=str(user.email), link=link, locale=user.locale
        )
        return ok(True)


# --- ResetPassword ---------------------------------------------------------


class ResetPassword:
    def __init__(
        self,
        users: UserRepository,
        email_tokens: EmailTokenRepository,
        refresh_tokens: RefreshTokenRepository,
    ) -> None:
        self._users = users
        self._email_tokens = email_tokens
        self._refresh_tokens = refresh_tokens

    async def execute(
        self, *, token: str, new_password: str, uow: UnitOfWork
    ) -> Result[bool, ValidationError | NotFoundError]:
        if len(new_password) < 10:
            return err(ValidationError("Password must be at least 10 characters"))
        token_h = hash_token(token)
        now = utc_now()
        user_id = await self._email_tokens.consume(
            token_hash=token_h, purpose="password_reset", now=now
        )
        if user_id is None:
            return err(ValidationError("Invalid or expired reset token"))
        user = await self._users.get_by_id(user_id)
        if user is None:
            return err(NotFoundError("User no longer exists"))
        user.change_password(hash_password(new_password), now=now)
        # Verify email if not yet (password reset implies email access)
        if not user.is_verified:
            user.mark_verified(now=now)
        await self._users.save(user)
        await self._refresh_tokens.revoke_all_for_user(user.id)
        uow.add_events(user.pop_events())
        return ok(True)


# --- DeleteAccount ---------------------------------------------------------


class DeleteAccount:
    def __init__(
        self,
        users: UserRepository,
        refresh_tokens: RefreshTokenRepository,
    ) -> None:
        self._users = users
        self._refresh_tokens = refresh_tokens

    async def execute(
        self, *, user_id: str, uow: UnitOfWork
    ) -> Result[bool, NotFoundError]:
        from uuid import UUID

        user = await self._users.get_by_id(UUID(user_id))
        if user is None:
            return err(NotFoundError("User not found"))
        user.soft_delete(now=utc_now())
        await self._users.save(user)
        await self._refresh_tokens.revoke_all_for_user(user.id)
        uow.add_events(user.pop_events())
        return ok(True)


# --- ExportUserData (RGPD Art. 20) ----------------------------------------


class ExportUserData:
    def __init__(self, exporter: UserDataExporter) -> None:
        self._exporter = exporter

    async def execute(self, *, user_id: str) -> Result[dict[str, Any], NotFoundError]:
        from uuid import UUID

        data = await self._exporter.export_all(UUID(user_id))
        if not data:
            return err(NotFoundError("User not found"))
        return ok(data)


# --- GetCurrentUser --------------------------------------------------------


@dataclass(frozen=True)
class CurrentUserDto:
    user_id: str
    email: str
    display_name: str | None
    locale: str
    email_verified: bool
    mfa_enabled: bool
    created_at: str


class GetCurrentUser:
    def __init__(self, users: UserRepository) -> None:
        self._users = users

    async def execute(self, *, user_id: str) -> Result[CurrentUserDto, NotFoundError]:
        from uuid import UUID

        user = await self._users.get_by_id(UUID(user_id))
        if user is None or user.is_deleted:
            return err(NotFoundError("User not found"))
        return ok(
            CurrentUserDto(
                user_id=str(user.id),
                email=str(user.email),
                display_name=user.display_name,
                locale=user.locale,
                email_verified=user.is_verified,
                mfa_enabled=user.mfa_enabled,
                created_at=user.created_at.isoformat(),
            )
        )
