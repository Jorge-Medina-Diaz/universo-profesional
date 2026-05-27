"""Integrations application ports."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Protocol
from uuid import UUID

from src.integrations.domain.external_account import ExternalAccount
from src.integrations.domain.linkedin_profile import LinkedInProfile


class LinkedInSyncProvider(Protocol):
    """Abstracts where the LinkedIn profile data comes from.

    Concrete implementations:
      * `DmaLinkedInProvider` — official EEA-only DMA 3rd-party API, free,
        requires LinkedIn approval. Needs the user to have authorized
        `r_dma_portability_3rd_party` via OAuth.
      * `ProxycurlLinkedInProvider` — paid 3rd party that scrapes public
        profiles legally. Works globally, gated behind PRO tier.

    Both return the same `LinkedInProfile` shape, so the mapper to universe
    entries doesn't care which path was used.
    """

    provider_id: str  # "linkedin_dma" | "linkedin_proxycurl"
    requires_pro: bool

    async def fetch_profile(
        self, *, user_id: UUID, account: ExternalAccount | None
    ) -> LinkedInProfile: ...


class ExternalAccountRepository(Protocol):
    async def get(self, user_id: UUID, provider: str) -> ExternalAccount | None: ...
    async def list_for_user(self, user_id: UUID) -> list[ExternalAccount]: ...
    async def upsert(self, account: ExternalAccount) -> None: ...
    async def delete(self, user_id: UUID, provider: str) -> bool: ...
    async def touch_sync(
        self,
        user_id: UUID,
        provider: str,
        *,
        ok: bool,
        error: str | None,
        when: datetime,
    ) -> None: ...


class SyncRunsRepository(Protocol):
    async def start(self, user_id: UUID, provider: str) -> UUID: ...
    async def finish(
        self,
        run_id: UUID,
        *,
        ok: bool,
        items_created: int,
        items_updated: int,
        error: str | None,
        summary: dict[str, Any] | None,
    ) -> None: ...
    async def list_for_user(self, user_id: UUID, limit: int = 10) -> list[dict[str, Any]]: ...
    async def is_cancelled(self, run_id: UUID) -> bool: ...


class OperationCancelledError(Exception):
    """Raised by long-running operations when the user has requested cancel.

    Sync workers should call `await self._runs.is_cancelled(run_id)` at each
    natural checkpoint and raise this when it returns True. The outer
    try/except in the sync use case will catch it and mark the run as
    `ok=False, error="cancelled"`.
    """


class ImportSessionRepository(Protocol):
    async def create(
        self, *, user_id: UUID, source: str, parsed: dict[str, Any]
    ) -> UUID: ...
    async def get(self, user_id: UUID, session_id: UUID) -> dict[str, Any] | None: ...
    async def mark_committed(self, session_id: UUID) -> None: ...
