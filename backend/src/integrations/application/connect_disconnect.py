"""Use cases for connecting and disconnecting external accounts."""
from __future__ import annotations

from typing import Any
from uuid import UUID

from src.integrations.application.ports import ExternalAccountRepository
from src.integrations.domain.external_account import (
    ExternalAccount,
    IntegrationConnected,
    IntegrationDisconnected,
)
from src.shared.errors import NotFoundError
from src.shared.result import Result, err, ok
from src.shared.security import utc_now
from src.shared.uow import UnitOfWork


class ConnectGithub:
    def __init__(self, accounts: ExternalAccountRepository) -> None:
        self._accounts = accounts

    async def execute(
        self,
        *,
        user_id: str,
        code: str,
        redirect_uri: str,
        uow: UnitOfWork,
    ) -> dict[str, Any]:
        from src.integrations.application.ports.github import (
            GithubClient,
            exchange_code_for_token,
        )
        from src.shared.config import get_settings

        settings = get_settings()
        if not settings.github_client_id or not settings.github_client_secret:
            raise RuntimeError(
                "GITHUB_CLIENT_ID/SECRET not configured. Set in .env to enable GitHub OAuth."
            )
        token_resp = await exchange_code_for_token(
            client_id=settings.github_client_id,
            client_secret=settings.github_client_secret,
            code=code,
            redirect_uri=redirect_uri,
        )
        if "access_token" not in token_resp:
            raise RuntimeError(f"GitHub token exchange failed: {token_resp}")

        access = token_resp["access_token"]
        scopes = (token_resp.get("scope") or "").split(",")
        gh = GithubClient(access)
        me = await gh.get_authenticated_user()

        uid = UUID(user_id)
        account = ExternalAccount.create(
            user_id=uid,
            provider="github",
            provider_user_id=str(me.get("id")) if me.get("id") else None,
            provider_username=me.get("login"),
            access_token=access,
            refresh_token=token_resp.get("refresh_token"),
            expires_at=None,
            scopes=[s.strip() for s in scopes if s.strip()],
            metadata={
                "name": me.get("name"),
                "bio": me.get("bio"),
                "avatar_url": me.get("avatar_url"),
                "html_url": me.get("html_url"),
                "company": me.get("company"),
                "location": me.get("location"),
            },
            now=utc_now(),
        )
        await self._accounts.upsert(account)
        uow.add_event(
            IntegrationConnected(
                user_id=uid,
                provider="github",
                provider_user_id=account.provider_user_id,
            )
        )
        return {
            "provider": "github",
            "username": account.provider_username,
            "scopes": account.scopes,
            "name": account.metadata.get("name"),
            "avatar_url": account.metadata.get("avatar_url"),
        }


class DisconnectAccount:
    def __init__(self, accounts: ExternalAccountRepository) -> None:
        self._accounts = accounts

    async def execute(
        self, *, user_id: str, provider: str, uow: UnitOfWork
    ) -> Result[bool, NotFoundError]:
        uid = UUID(user_id)
        removed = await self._accounts.delete(uid, provider)
        if not removed:
            return err(NotFoundError(f"No {provider} account connected"))
        uow.add_event(IntegrationDisconnected(user_id=uid, provider=provider))
        return ok(True)


class ListConnections:
    def __init__(self, accounts: ExternalAccountRepository) -> None:
        self._accounts = accounts

    async def execute(self, *, user_id: str) -> list[dict[str, Any]]:
        items = await self._accounts.list_for_user(UUID(user_id))
        return [
            {
                "provider": a.provider,
                "username": a.provider_username,
                "scopes": a.scopes,
                "connected_at": a.connected_at.isoformat(),
                "last_synced_at": a.last_synced_at.isoformat() if a.last_synced_at else None,
                "sync_status": a.sync_status,
                "sync_error": a.sync_error,
                "metadata": {
                    "name": a.metadata.get("name"),
                    "avatar_url": a.metadata.get("avatar_url"),
                    "html_url": a.metadata.get("html_url"),
                },
            }
            for a in items
        ]
