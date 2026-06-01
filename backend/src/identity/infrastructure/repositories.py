"""SQLAlchemy implementations of Identity ports."""
from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.identity.application.ports import (
    EmailTokenRepository,
    RefreshTokenRepository,
    UserRepository,
)
from src.identity.domain.user import User
from src.identity.infrastructure.orm import EmailTokenOrm, RefreshTokenOrm, UserOrm
from src.shared.security import utc_now
from src.shared.value_objects import Email


def _to_domain(row: UserOrm) -> User:
    return User(
        id=row.id,
        email=Email(row.email),
        password_hash=row.password_hash,
        display_name=row.display_name,
        locale=row.locale,
        email_verified_at=row.email_verified_at,
        mfa_secret=row.mfa_secret,
        mfa_enabled=row.mfa_enabled,
        created_at=row.created_at,
        updated_at=row.updated_at,
        deleted_at=row.deleted_at,
        last_login_at=row.last_login_at,
        tier=getattr(row, "tier", "free") or "free",
        tier_updated_at=getattr(row, "tier_updated_at", None),
        onboarding_started_at=getattr(row, "onboarding_started_at", None),
        activated_at=getattr(row, "activated_at", None),
        onboarding_completed_at=getattr(row, "onboarding_completed_at", None),
    )


class SqlAlchemyUserRepository(UserRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, user_id: UUID) -> User | None:
        row = await self._session.get(UserOrm, user_id)
        return _to_domain(row) if row else None

    async def get_by_email(self, email: str) -> User | None:
        stmt = select(UserOrm).where(UserOrm.email == email)
        row = (await self._session.execute(stmt)).scalar_one_or_none()
        return _to_domain(row) if row else None

    async def save(self, user: User) -> None:
        existing = await self._session.get(UserOrm, user.id)
        if existing is None:
            self._session.add(
                UserOrm(
                    id=user.id,
                    email=str(user.email),
                    password_hash=user.password_hash,
                    display_name=user.display_name,
                    locale=user.locale,
                    email_verified_at=user.email_verified_at,
                    mfa_secret=user.mfa_secret,
                    mfa_enabled=user.mfa_enabled,
                    created_at=user.created_at,
                    updated_at=user.updated_at,
                    deleted_at=user.deleted_at,
                    last_login_at=user.last_login_at,
                    tier=user.tier,
                    tier_updated_at=user.tier_updated_at,
                    onboarding_started_at=user.onboarding_started_at,
                    activated_at=user.activated_at,
                    onboarding_completed_at=user.onboarding_completed_at,
                )
            )
        else:
            existing.email = str(user.email)
            existing.password_hash = user.password_hash
            existing.display_name = user.display_name
            existing.locale = user.locale
            existing.email_verified_at = user.email_verified_at
            existing.mfa_secret = user.mfa_secret
            existing.mfa_enabled = user.mfa_enabled
            existing.updated_at = user.updated_at
            existing.deleted_at = user.deleted_at
            existing.last_login_at = user.last_login_at
            existing.tier = user.tier
            existing.tier_updated_at = user.tier_updated_at
            existing.onboarding_started_at = user.onboarding_started_at
            existing.activated_at = user.activated_at
            existing.onboarding_completed_at = user.onboarding_completed_at
        await self._session.flush()

    async def hard_delete_expired(self, before: datetime) -> int:
        stmt = (
            delete(UserOrm)
            .where(UserOrm.deleted_at.is_not(None))
            .where(UserOrm.deleted_at < before)
            .returning(UserOrm.id)
        )
        result = await self._session.execute(stmt)
        return len(result.fetchall())

    async def count_activation_signals(self, user_id: UUID) -> dict[str, int]:
        # Raw SQL so identity.infrastructure derives activation from real data
        # without importing other bounded contexts (import-linter stays clean).
        from sqlalchemy import text as _sql_text

        row = (
            await self._session.execute(
                _sql_text(
                    "SELECT "
                    "(SELECT count(*) FROM experiences WHERE user_id = :uid) AS experiences, "
                    "(SELECT count(*) FROM skills WHERE user_id = :uid) AS skills, "
                    "(SELECT count(*) FROM documents WHERE user_id = :uid AND kind = 'cv') AS cvs"
                ),
                {"uid": str(user_id)},
            )
        ).one()
        return {
            "experiences": int(row.experiences),
            "skills": int(row.skills),
            "cvs": int(row.cvs),
        }


class SqlAlchemyEmailTokenRepository(EmailTokenRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(
        self,
        *,
        user_id: UUID,
        token_hash: str,
        purpose: str,
        expires_at: datetime,
    ) -> None:
        self._session.add(
            EmailTokenOrm(
                token_hash=token_hash,
                user_id=user_id,
                purpose=purpose,
                expires_at=expires_at,
                used_at=None,
                created_at=utc_now(),
            )
        )
        await self._session.flush()

    async def consume(
        self, *, token_hash: str, purpose: str, now: datetime
    ) -> UUID | None:
        stmt = (
            update(EmailTokenOrm)
            .where(EmailTokenOrm.token_hash == token_hash)
            .where(EmailTokenOrm.purpose == purpose)
            .where(EmailTokenOrm.used_at.is_(None))
            .where(EmailTokenOrm.expires_at > now)
            .values(used_at=now)
            .returning(EmailTokenOrm.user_id)
        )
        result = await self._session.execute(stmt)
        row = result.first()
        return row[0] if row else None


class SqlAlchemyRefreshTokenRepository(RefreshTokenRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def store(
        self,
        *,
        user_id: UUID,
        token_hash: str,
        expires_at: datetime,
        user_agent: str | None,
        ip_address: str | None,
    ) -> None:
        self._session.add(
            RefreshTokenOrm(
                token_hash=token_hash,
                user_id=user_id,
                issued_at=utc_now(),
                expires_at=expires_at,
                revoked_at=None,
                replaced_by=None,
                user_agent=user_agent,
                ip_address=ip_address,
            )
        )
        await self._session.flush()

    async def rotate(
        self,
        *,
        old_token_hash: str,
        new_token_hash: str,
        new_expires_at: datetime,
        user_agent: str | None,
        ip_address: str | None,
    ) -> UUID | None:
        """Rotate a refresh token. Detects reuse and burns the chain.

        OAuth 2.0 refresh-token rotation security model (RFC 6749 §10.4 +
        OAuth 2.1 §6.1): when a refresh token is rotated, the OLD one is
        invalidated. If a request arrives later for that same OLD token,
        we have two possibilities:
          1. The legitimate user is replaying it (browser session lost
             the new token before persisting). Unlikely but possible.
          2. An attacker stole the old token before rotation. Almost
             certain when (1) is unlikely.

        Both cases warrant the same response: revoke EVERY refresh token
        for the user (force re-login). This kills the attacker's session
        AND any legitimate ones — annoying but the only safe default.
        """
        now = utc_now()
        # Look up the token without filters to inspect its state.
        existing = (
            await self._session.execute(
                select(RefreshTokenOrm).where(
                    RefreshTokenOrm.token_hash == old_token_hash
                )
            )
        ).scalar_one_or_none()
        if existing is None:
            return None

        # Reuse detection: token was already rotated (revoked + replaced_by set).
        if existing.replaced_by is not None or existing.revoked_at is not None:
            await self._session.execute(
                update(RefreshTokenOrm)
                .where(RefreshTokenOrm.user_id == existing.user_id)
                .where(RefreshTokenOrm.revoked_at.is_(None))
                .values(revoked_at=now)
            )
            await self._session.flush()
            return None

        if existing.expires_at <= now:
            return None

        # Happy path — mark old as rotated, mint new.
        existing.revoked_at = now
        existing.replaced_by = new_token_hash
        self._session.add(
            RefreshTokenOrm(
                token_hash=new_token_hash,
                user_id=existing.user_id,
                issued_at=now,
                expires_at=new_expires_at,
                revoked_at=None,
                replaced_by=None,
                user_agent=user_agent,
                ip_address=ip_address,
            )
        )
        await self._session.flush()
        return existing.user_id

    async def revoke(self, token_hash: str) -> None:
        stmt = (
            update(RefreshTokenOrm)
            .where(RefreshTokenOrm.token_hash == token_hash)
            .where(RefreshTokenOrm.revoked_at.is_(None))
            .values(revoked_at=utc_now())
        )
        await self._session.execute(stmt)

    async def revoke_all_for_user(self, user_id: UUID) -> None:
        stmt = (
            update(RefreshTokenOrm)
            .where(RefreshTokenOrm.user_id == user_id)
            .where(RefreshTokenOrm.revoked_at.is_(None))
            .values(revoked_at=utc_now())
        )
        await self._session.execute(stmt)
