"""LinkedIn OIDC sign-in flow.

Two paths converge in `handle_callback`:
  1. Brand new user → create account, auto-verify email, return JWT.
  2. Existing user with same email → log them in (no password change), store
     the OIDC access token in `external_accounts` as `linkedin_oidc` for future
     re-authorization escalation (e.g. DMA scope upgrade).

State handling: we use a signed state JWT (5-minute TTL) so we can safely round-trip
arbitrary metadata (e.g. "link to existing user_id" vs "fresh signup"). The state
is opaque to the user; we issue it from `/auth/linkedin/authorize`.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from uuid import UUID, uuid4

import structlog
from jose import JWTError

from src.identity.application.ports import (
    RefreshTokenRepository,
    UserRepository,
)
from src.identity.application.use_cases import LoginTokens
from src.identity.domain.user import User
from src.integrations.application.ports import ExternalAccountRepository
from src.integrations.domain.external_account import (
    ExternalAccount,
    IntegrationConnected,
)
from src.shared.config import get_settings
from src.shared.errors import UnauthorizedError, ValidationError
from src.shared.result import Result, err, ok
from src.shared.security import (
    decode_jwt,
    encode_jwt,
    generate_token,
    hash_token,
    utc_in,
    utc_now,
)
from src.shared.uow import UnitOfWork
from src.shared.value_objects import Email

logger = structlog.get_logger(__name__)


def _state_aud() -> str:
    return "cvs-saas-oidc-state"


def issue_state(*, link_user_id: str | None = None) -> str:
    """Sign a short-lived state token.

    If `link_user_id` is set, the callback will attach the LinkedIn account to
    that user (used when an authed user clicks "Connect LinkedIn" inside the
    app). Otherwise, callback runs the sign-in/sign-up flow.
    """
    now = utc_now()
    payload = {
        "jti": str(uuid4()),
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=5)).timestamp()),
        "aud": _state_aud(),
        "iss": get_settings().canonical_base_url,
        "link_user_id": link_user_id,
    }
    return encode_jwt(payload)


def parse_state(token: str) -> dict:
    try:
        return decode_jwt(token, audience=_state_aud())
    except JWTError as exc:
        raise ValidationError(f"Invalid OIDC state: {exc}") from exc


@dataclass(frozen=True)
class OidcSignInResult:
    tokens: LoginTokens
    created: bool  # True if a new user was created
    linked: bool  # True if linked to an existing authed user


class LinkedInOidcSignIn:
    """Use case: handle LinkedIn OIDC callback — sign in / sign up / link."""

    def __init__(
        self,
        users: UserRepository,
        refresh_tokens: RefreshTokenRepository,
        accounts: ExternalAccountRepository,
    ) -> None:
        self._users = users
        self._refresh_tokens = refresh_tokens
        self._accounts = accounts

    async def execute(
        self,
        *,
        userinfo: dict,
        access_token: str,
        expires_in: int | None,
        user_agent: str | None,
        ip_address: str | None,
        state: dict,
        uow: UnitOfWork,
    ) -> Result[OidcSignInResult, UnauthorizedError | ValidationError]:
        sub = userinfo.get("sub")
        email_raw = userinfo.get("email")
        if not sub or not email_raw:
            return err(ValidationError("LinkedIn OIDC userinfo missing sub or email"))

        try:
            email_vo = Email.parse(email_raw)
        except ValidationError as exc:
            return err(exc)

        now = utc_now()
        existing_user = await self._users.get_by_email(str(email_vo))
        link_user_id = state.get("link_user_id")

        created = False
        linked_existing = False

        if link_user_id:
            # User is authed and is linking LinkedIn — must match the email
            user = await self._users.get_by_id(UUID(link_user_id))
            if user is None or user.is_deleted:
                return err(UnauthorizedError("Authed user no longer exists"))
            if existing_user is not None and existing_user.id != user.id:
                return err(
                    ValidationError(
                        "LinkedIn email is already linked to another account. "
                        "Disconnect from the other account first."
                    )
                )
            # Allow linking to a different email if user hasn't a LinkedIn account yet
            linked_existing = True
        elif existing_user is None:
            # Sign up — create the user. No password (OAuth-only until they set one).
            display = userinfo.get("name") or (
                f"{userinfo.get('given_name','')} {userinfo.get('family_name','')}".strip() or None
            )
            locale_info = userinfo.get("locale") or {}
            locale_str = "es-ES"
            if isinstance(locale_info, dict):
                lang = locale_info.get("language")
                country = locale_info.get("country")
                if lang and country:
                    locale_str = f"{lang}-{country}"
                elif lang:
                    locale_str = lang
            elif isinstance(locale_info, str):
                locale_str = locale_info

            user = User.register(
                email=email_vo,
                password_hash=None,
                display_name=display,
                locale=locale_str,
                now=now,
            )
            # OIDC-verified email → mark verified immediately
            user.mark_verified(now=now)
            await self._users.save(user)
            created = True
        else:
            # Sign in — existing user, verify on first OIDC sign-in if not yet
            if existing_user.is_deleted:
                return err(UnauthorizedError("Account is deleted"))
            user = existing_user
            if not user.is_verified:
                user.mark_verified(now=now)
                await self._users.save(user)

        # Store / update the external_accounts entry for linkedin_oidc
        account = ExternalAccount.create(
            user_id=user.id,
            provider="linkedin_oidc",
            provider_user_id=sub,
            provider_username=userinfo.get("name"),
            access_token=access_token,
            refresh_token=None,  # OIDC v2 doesn't issue refresh tokens
            expires_at=utc_now() + timedelta(seconds=int(expires_in or 3600 * 24 * 60)),
            scopes=["openid", "profile", "email"],
            metadata={
                "picture": userinfo.get("picture"),
                "given_name": userinfo.get("given_name"),
                "family_name": userinfo.get("family_name"),
                "locale": userinfo.get("locale"),
                "email_verified": userinfo.get("email_verified"),
            },
            now=now,
        )
        await self._accounts.upsert(account)
        uow.add_event(IntegrationConnected(user_id=user.id, provider="linkedin_oidc"))

        # Issue our own JWT pair
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
            OidcSignInResult(
                tokens=LoginTokens(
                    access_token=access,
                    refresh_token=refresh,
                    user_id=str(user.id),
                    email=str(user.email),
                ),
                created=created,
                linked=linked_existing,
            )
        )
