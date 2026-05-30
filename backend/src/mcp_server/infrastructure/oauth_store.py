"""Persistence layer for OAuth clients, codes, tokens, invocations."""
from __future__ import annotations

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.mcp_server.infrastructure.orm import (
    McpInvocationOrm,
    OAuthAuthorizationCodeOrm,
    OAuthClientOrm,
    OAuthTokenOrm,
)
from src.shared.security import hash_token, utc_now


class OAuthStore:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    # --- Clients (DCR) ----------------------------------------------------

    async def register_client(
        self,
        *,
        client_name: str,
        redirect_uris: list[str],
        scopes: list[str],
        grant_types: list[str] | None = None,
        token_endpoint_auth_method: str = "none",
        software_id: str | None = None,
        software_version: str | None = None,
    ) -> UUID:
        client_id = uuid4()
        self._session.add(
            OAuthClientOrm(
                client_id=client_id,
                user_id=None,
                client_name=client_name,
                redirect_uris=redirect_uris,
                grant_types=grant_types or ["authorization_code", "refresh_token"],
                scopes=scopes,
                client_secret_hash=None,
                token_endpoint_auth_method=token_endpoint_auth_method,
                software_id=software_id,
                software_version=software_version,
                registered_at=utc_now(),
                last_used_at=None,
            )
        )
        await self._session.flush()
        return client_id

    async def get_client(self, client_id: UUID) -> OAuthClientOrm | None:
        return await self._session.get(OAuthClientOrm, client_id)

    async def touch_client(self, client_id: UUID) -> None:
        stmt = (
            update(OAuthClientOrm)
            .where(OAuthClientOrm.client_id == client_id)
            .values(last_used_at=utc_now())
        )
        await self._session.execute(stmt)

    # --- Authorization codes ---------------------------------------------

    async def store_code(
        self,
        *,
        code: str,
        client_id: UUID,
        user_id: UUID,
        redirect_uri: str,
        scopes: list[str],
        resource: str,
        code_challenge: str,
        code_challenge_method: str,
        expires_at: datetime,
    ) -> None:
        self._session.add(
            OAuthAuthorizationCodeOrm(
                code_hash=hash_token(code),
                client_id=client_id,
                user_id=user_id,
                redirect_uri=redirect_uri,
                scopes=scopes,
                resource=resource,
                code_challenge=code_challenge,
                code_challenge_method=code_challenge_method,
                expires_at=expires_at,
                consumed_at=None,
                created_at=utc_now(),
            )
        )
        await self._session.flush()

    async def consume_code(
        self, *, code: str, client_id: UUID, code_verifier: str
    ) -> OAuthAuthorizationCodeOrm | None:
        import base64
        import hashlib

        stmt = (
            select(OAuthAuthorizationCodeOrm)
            .where(OAuthAuthorizationCodeOrm.code_hash == hash_token(code))
            .where(OAuthAuthorizationCodeOrm.client_id == client_id)
        )
        row = (await self._session.execute(stmt)).scalar_one_or_none()
        if row is None or row.consumed_at is not None or row.expires_at < utc_now():
            return None
        # PKCE verification — OAuth 2.1 mandates S256 and forbids `plain`.
        # Reject any non-S256 method outright: the well-known metadata only
        # advertises S256, so a `plain` challenge is a downgrade attempt.
        if row.code_challenge_method != "S256":
            return None
        expected = (
            base64.urlsafe_b64encode(hashlib.sha256(code_verifier.encode()).digest())
            .rstrip(b"=")
            .decode()
        )
        if expected != row.code_challenge:
            return None
        row.consumed_at = utc_now()
        await self._session.flush()
        return row

    # --- Tokens ----------------------------------------------------------

    async def store_token(
        self,
        *,
        token: str,
        kind: str,
        user_id: UUID,
        client_id: UUID,
        scopes: list[str],
        resource: str,
        expires_at: datetime,
        replaced_by: str | None = None,
    ) -> None:
        self._session.add(
            OAuthTokenOrm(
                token_hash=hash_token(token),
                user_id=user_id,
                client_id=client_id,
                kind=kind,
                scopes=scopes,
                resource=resource,
                expires_at=expires_at,
                revoked_at=None,
                issued_at=utc_now(),
                replaced_by=replaced_by,
            )
        )
        await self._session.flush()

    async def get_token(self, token: str) -> OAuthTokenOrm | None:
        return await self._session.get(OAuthTokenOrm, hash_token(token))

    async def revoke_token(self, token: str) -> None:
        stmt = (
            update(OAuthTokenOrm)
            .where(OAuthTokenOrm.token_hash == hash_token(token))
            .values(revoked_at=utc_now())
        )
        await self._session.execute(stmt)

    async def revoke_all_for_user(self, user_id: UUID) -> int:
        """Revoke every live MCP access + refresh token for a user (e.g. on
        account deletion). Returns the number revoked."""
        stmt = (
            update(OAuthTokenOrm)
            .where(OAuthTokenOrm.user_id == user_id)
            .where(OAuthTokenOrm.revoked_at.is_(None))
            .values(revoked_at=utc_now())
            .returning(OAuthTokenOrm.token_hash)
        )
        result = await self._session.execute(stmt)
        return len(result.fetchall())

    async def rotate_refresh(
        self,
        *,
        refresh: str,
        new_refresh: str,
        client_id: UUID,
        new_expires_at: datetime,
    ) -> OAuthTokenOrm | None:
        old_h = hash_token(refresh)

        # Reuse detection (RFC 6819 §5.2.2.3): if the presented refresh token
        # exists but was already rotated (replaced_by set) or revoked, it's a
        # replay — burn the whole token chain for this (user, client) so a
        # leaked token can't be used to mint a parallel session. Mirrors the
        # browser refresh path in identity.
        existing = (
            await self._session.execute(
                select(OAuthTokenOrm).where(OAuthTokenOrm.token_hash == old_h)
            )
        ).scalar_one_or_none()
        if existing is not None and (
            existing.replaced_by is not None or existing.revoked_at is not None
        ):
            await self._session.execute(
                update(OAuthTokenOrm)
                .where(OAuthTokenOrm.user_id == existing.user_id)
                .where(OAuthTokenOrm.client_id == existing.client_id)
                .where(OAuthTokenOrm.revoked_at.is_(None))
                .values(revoked_at=utc_now())
            )
            return None

        stmt = (
            update(OAuthTokenOrm)
            .where(OAuthTokenOrm.token_hash == old_h)
            .where(OAuthTokenOrm.client_id == client_id)
            .where(OAuthTokenOrm.kind == "refresh")
            .where(OAuthTokenOrm.revoked_at.is_(None))
            .where(OAuthTokenOrm.expires_at > utc_now())
            .values(revoked_at=utc_now(), replaced_by=hash_token(new_refresh))
            .returning(OAuthTokenOrm)
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    # --- Invocations -----------------------------------------------------

    async def log_invocation(
        self,
        *,
        user_id: UUID,
        client_id: UUID | None,
        tool_name: str,
        ok: bool,
        latency_ms: int | None,
        error_code: str | None = None,
    ) -> None:
        self._session.add(
            McpInvocationOrm(
                id=uuid4(),
                user_id=user_id,
                client_id=client_id,
                tool_name=tool_name,
                ok=ok,
                latency_ms=latency_ms,
                error_code=error_code,
                created_at=utc_now(),
            )
        )
        await self._session.flush()
