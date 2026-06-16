"""Identity use cases — pure application logic over ports.

Each use case is a callable class with an `execute()` method returning a
Result. Mapping to HTTP / MCP happens in the interfaces layer.
"""
from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any
from uuid import UUID

from src.identity.application.ports import (
    EmailSender,
    EmailTokenRepository,
    RefreshTokenRepository,
    UserDataExporter,
    UserRepository,
)
from src.identity.domain.user import User
from src.shared import totp
from src.shared.config import get_settings
from src.shared.errors import (
    ConflictError,
    NotFoundError,
    UnauthorizedError,
    ValidationError,
)
from src.shared.fernet import decrypt as _fernet_decrypt
from src.shared.fernet import encrypt as _fernet_encrypt
from src.shared.metrics import user_registered_total
from src.shared.result import Result, err, ok
from src.shared.security import (
    decode_jwt,
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

# Distinct audience for the short-lived token minted after a correct password
# when MFA is enabled — it is exchanged for real session tokens via /auth/mfa
# and must never be accepted as an access token.
_MFA_AUDIENCE = "cvs-saas-mfa"
_MFA_TTL_MINUTES = 5


def _encrypt_mfa_secret(secret: str) -> str:
    """Fernet-encrypt a TOTP secret for at-rest storage in users.mfa_secret."""
    return _fernet_encrypt(secret).decode("ascii")


def _decrypt_mfa_secret(stored: str) -> str:
    return _fernet_decrypt(stored.encode("ascii"))


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

        settings = get_settings()
        # Dev/test: auto-verify so the user can log in immediately. Saves a trip
        # to Mailhog / hunting for the verification_link in the response.
        if (settings.is_dev or settings.is_test) and settings.auto_verify_emails_in_dev:
            user.mark_verified(now=now)

        await self._users.save(user)

        # Email verification token (24h, single use) — always create one so the
        # link is available for QA, even if auto-verify is on.
        token = generate_token()
        token_h = hash_token(token)
        await self._email_tokens.create(
            user_id=user.id,
            token_hash=token_h,
            purpose="verify_email",
            expires_at=utc_in(hours=24),
        )

        link = f"{settings.frontend_base_url}/#/auth/verify?token={token}"
        # Only send the email when we haven't already verified the user; cuts
        # the Mailhog spam in dev to actual auth flows (password reset, etc).
        if not user.is_verified:
            await self._emailer.send_verification(to=str(user.email), link=link, locale=locale)

        uow.add_events(user.pop_events())
        user_registered_total.inc()
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
        welcome_emailer: Callable[[UUID], Awaitable[None]] | None = None,
    ) -> None:
        self._users = users
        self._email_tokens = email_tokens
        self._welcome_emailer = welcome_emailer

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
        was_unverified = not user.is_verified
        user.mark_verified(now=now)
        await self._users.save(user)
        uow.add_events(user.pop_events())

        # Send the welcome email exactly once — when a user transitions from
        # unverified → verified. We swallow errors here so verification itself
        # always succeeds; the email worker handles retries.
        if was_unverified and self._welcome_emailer is not None:
            try:
                await self._welcome_emailer(user.id)
            except Exception:
                pass
        return ok(True)


# --- Login -----------------------------------------------------------------


@dataclass(frozen=True)
class LoginTokens:
    access_token: str
    refresh_token: str
    user_id: str
    email: str
    # When MFA is enabled the password step returns no session tokens; instead
    # mfa_required=True + a short-lived mfa_token the client exchanges for the
    # real pair via /auth/mfa.
    mfa_required: bool = False
    mfa_token: str | None = None


async def _issue_session_tokens(
    refresh_tokens: RefreshTokenRepository,
    user: User,
    *,
    now: Any,
    user_agent: str | None,
    ip_address: str | None,
    uow: UnitOfWork,
) -> LoginTokens:
    """Mint the access + refresh pair for a fully-authenticated user.

    Shared by the password-only path (`Login`) and the MFA completion path
    (`CompleteMfaLogin`) so token issuance lives in exactly one place.
    """
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
    await refresh_tokens.store(
        user_id=user.id,
        token_hash=refresh_h,
        expires_at=refresh_exp,
        user_agent=user_agent,
        ip_address=ip_address,
    )
    uow.add_events(user.pop_events())
    return LoginTokens(
        access_token=access,
        refresh_token=refresh,
        user_id=str(user.id),
        email=str(user.email),
    )


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

        # MFA gate: password is correct, but if the user enrolled a second
        # factor we must NOT hand out session tokens yet. Mint a short-lived,
        # single-purpose mfa_token the client exchanges (with the TOTP code)
        # via /auth/mfa. record_login is deferred until the factor is verified.
        if user.mfa_enabled and user.mfa_secret:
            now = utc_now()
            settings = get_settings()
            mfa_token = encode_jwt(
                {
                    "sub": str(user.id),
                    "iss": settings.canonical_base_url,
                    "aud": _MFA_AUDIENCE,
                    "iat": int(now.timestamp()),
                    "exp": int(utc_in(minutes=_MFA_TTL_MINUTES).timestamp()),
                    "purpose": "mfa",
                }
            )
            return ok(
                LoginTokens(
                    access_token="",
                    refresh_token="",
                    user_id=str(user.id),
                    email=str(user.email),
                    mfa_required=True,
                    mfa_token=mfa_token,
                )
            )

        now = utc_now()
        user.record_login(now=now)
        await self._users.save(user)
        return ok(
            await _issue_session_tokens(
                self._refresh_tokens,
                user,
                now=now,
                user_agent=user_agent,
                ip_address=ip_address,
                uow=uow,
            )
        )


class CompleteMfaLogin:
    """Second step of an MFA login: exchange (mfa_token, code) for tokens."""

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
        mfa_token: str,
        code: str,
        user_agent: str | None,
        ip_address: str | None,
        uow: UnitOfWork,
    ) -> Result[LoginTokens, UnauthorizedError]:
        try:
            claims = decode_jwt(mfa_token, audience=_MFA_AUDIENCE)
        except Exception:
            return err(UnauthorizedError("Invalid or expired MFA token"))
        if claims.get("purpose") != "mfa" or not claims.get("sub"):
            return err(UnauthorizedError("Invalid MFA token"))

        user = await self._users.get_by_id(UUID(str(claims["sub"])))
        if (
            user is None
            or user.is_deleted
            or not user.mfa_enabled
            or not user.mfa_secret
        ):
            return err(UnauthorizedError("MFA not available"))

        secret = _decrypt_mfa_secret(user.mfa_secret)
        if not totp.verify(secret, code):
            return err(UnauthorizedError("Invalid MFA code"))

        now = utc_now()
        user.record_login(now=now)
        await self._users.save(user)
        return ok(
            await _issue_session_tokens(
                self._refresh_tokens,
                user,
                now=now,
                user_agent=user_agent,
                ip_address=ip_address,
                uow=uow,
            )
        )


@dataclass(frozen=True)
class MfaSetup:
    secret: str
    otpauth_uri: str


class SetupMfa:
    """Begin MFA enrolment: generate + store an (unconfirmed) secret."""

    def __init__(self, users: UserRepository) -> None:
        self._users = users

    async def execute(self, *, user_id: str) -> Result[MfaSetup, NotFoundError | ConflictError]:
        user = await self._users.get_by_id(UUID(user_id))
        if user is None or user.is_deleted:
            return err(NotFoundError("User not found"))
        if user.mfa_enabled:
            return err(ConflictError("MFA already enabled"))
        secret = totp.generate_secret()
        user.mfa_secret = _encrypt_mfa_secret(secret)
        user.mfa_enabled = False
        await self._users.save(user)
        return ok(
            MfaSetup(
                secret=secret,
                otpauth_uri=totp.provisioning_uri(secret, account_name=str(user.email)),
            )
        )


class ConfirmMfa:
    """Finish enrolment: verify a code against the pending secret, enable MFA."""

    def __init__(self, users: UserRepository) -> None:
        self._users = users

    async def execute(
        self, *, user_id: str, code: str
    ) -> Result[bool, NotFoundError | UnauthorizedError]:
        user = await self._users.get_by_id(UUID(user_id))
        if user is None or user.is_deleted:
            return err(NotFoundError("User not found"))
        if not user.mfa_secret:
            return err(UnauthorizedError("MFA setup not started"))
        secret = _decrypt_mfa_secret(user.mfa_secret)
        if not totp.verify(secret, code):
            return err(UnauthorizedError("Invalid MFA code"))
        user.mfa_enabled = True
        await self._users.save(user)
        return ok(True)


class DisableMfa:
    """Turn MFA off — requires a valid current code to prevent lockout abuse."""

    def __init__(self, users: UserRepository) -> None:
        self._users = users

    async def execute(
        self, *, user_id: str, code: str
    ) -> Result[bool, NotFoundError | UnauthorizedError]:
        user = await self._users.get_by_id(UUID(user_id))
        if user is None or user.is_deleted:
            return err(NotFoundError("User not found"))
        if not user.mfa_enabled or not user.mfa_secret:
            return err(UnauthorizedError("MFA is not enabled"))
        secret = _decrypt_mfa_secret(user.mfa_secret)
        if not totp.verify(secret, code):
            return err(UnauthorizedError("Invalid MFA code"))
        user.mfa_secret = None
        user.mfa_enabled = False
        await self._users.save(user)
        return ok(True)


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
        # Hash-router prefix (mirrors the verify link) — without it the SPA boots
        # at "#/" and the ?token is dropped, losing the reset token.
        link = f"{settings.frontend_base_url}/#/auth/reset?token={token}"
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
    tier: str = "free"
    tier_updated_at: str | None = None
    onboarding_started_at: str | None = None
    activated_at: str | None = None
    onboarding_completed_at: str | None = None


def _iso_or_none(value: Any) -> str | None:
    return value.isoformat() if value else None


def _current_user_dto(user: User) -> CurrentUserDto:
    return CurrentUserDto(
        user_id=str(user.id),
        email=str(user.email),
        display_name=user.display_name,
        locale=user.locale,
        email_verified=user.is_verified,
        mfa_enabled=user.mfa_enabled,
        created_at=user.created_at.isoformat(),
        tier=user.tier,
        tier_updated_at=_iso_or_none(user.tier_updated_at),
        onboarding_started_at=_iso_or_none(user.onboarding_started_at),
        activated_at=_iso_or_none(user.activated_at),
        onboarding_completed_at=_iso_or_none(user.onboarding_completed_at),
    )


class GetCurrentUser:
    def __init__(self, users: UserRepository) -> None:
        self._users = users

    async def execute(self, *, user_id: str) -> Result[CurrentUserDto, NotFoundError]:
        user = await self._users.get_by_id(UUID(user_id))
        if user is None or user.is_deleted:
            return err(NotFoundError("User not found"))
        return ok(_current_user_dto(user))


class SetUserTier:
    """Set the subscription tier directly (dev/admin use; in prod this is
    driven by Stripe webhooks). Idempotent."""

    def __init__(self, users: UserRepository) -> None:
        self._users = users

    async def execute(
        self, *, user_id: str, tier: str, uow: UnitOfWork
    ) -> Result[CurrentUserDto, NotFoundError | ValidationError]:
        from src.identity.domain.user import VALID_TIERS

        if tier not in VALID_TIERS:
            return err(ValidationError(f"Unsupported tier: {tier}"))
        user = await self._users.get_by_id(UUID(user_id))
        if user is None or user.is_deleted:
            return err(NotFoundError("User not found"))
        user.set_tier(tier, now=utc_now())
        await self._users.save(user)
        uow.add_events(user.pop_events())
        return ok(_current_user_dto(user))


class AdvanceOnboarding:
    """Server-side onboarding/activation state.

    Derives activation from the user's real signals (>=1 experience OR >=3
    skills OR 1 CV) and optionally marks onboarding complete (the explicit
    "finished the wizard" signal). Idempotent — safe to call on every
    onboarding touchpoint, cross-device, replacing the old localStorage flag.
    """

    def __init__(self, users: UserRepository) -> None:
        self._users = users

    async def execute(
        self, *, user_id: str, complete: bool, uow: UnitOfWork
    ) -> Result[CurrentUserDto, NotFoundError]:
        now = utc_now()
        user = await self._users.get_by_id(UUID(user_id))
        if user is None or user.is_deleted:
            return err(NotFoundError("User not found"))
        user.start_onboarding(now=now)
        signals = await self._users.count_activation_signals(user.id)
        if signals["experiences"] >= 1 or signals["skills"] >= 3 or signals["cvs"] >= 1:
            user.mark_activated(now=now)
        if complete:
            user.complete_onboarding(now=now)
        await self._users.save(user)
        uow.add_events(user.pop_events())
        return ok(_current_user_dto(user))
