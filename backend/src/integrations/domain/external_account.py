"""External account aggregate + events."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, ClassVar, Literal
from uuid import UUID, uuid4

from src.shared.events import DomainEvent

Provider = Literal["github", "linkedin", "linkedin_dma", "gitlab", "bitbucket"]


@dataclass(frozen=True, kw_only=True)
class IntegrationConnected(DomainEvent):
    event_type: ClassVar[str] = "integrations.connected"
    provider: str = ""
    provider_user_id: str | None = None


@dataclass(frozen=True, kw_only=True)
class IntegrationDisconnected(DomainEvent):
    event_type: ClassVar[str] = "integrations.disconnected"
    provider: str = ""


@dataclass(frozen=True, kw_only=True)
class IntegrationSynced(DomainEvent):
    event_type: ClassVar[str] = "integrations.synced"
    provider: str = ""
    items_created: int = 0
    items_updated: int = 0


@dataclass
class ExternalAccount:
    id: UUID
    user_id: UUID
    provider: str
    provider_user_id: str | None
    provider_username: str | None
    access_token: str | None  # plaintext in memory only — never persisted as such
    refresh_token: str | None
    expires_at: datetime | None
    scopes: list[str]
    metadata: dict[str, Any]
    connected_at: datetime
    last_synced_at: datetime | None
    sync_status: str | None
    sync_error: str | None

    @classmethod
    def create(
        cls,
        *,
        user_id: UUID,
        provider: str,
        provider_user_id: str | None,
        provider_username: str | None,
        access_token: str,
        refresh_token: str | None,
        expires_at: datetime | None,
        scopes: list[str],
        metadata: dict[str, Any],
        now: datetime,
    ) -> ExternalAccount:
        return cls(
            id=uuid4(),
            user_id=user_id,
            provider=provider,
            provider_user_id=provider_user_id,
            provider_username=provider_username,
            access_token=access_token,
            refresh_token=refresh_token,
            expires_at=expires_at,
            scopes=scopes,
            metadata=metadata,
            connected_at=now,
            last_synced_at=None,
            sync_status=None,
            sync_error=None,
        )
