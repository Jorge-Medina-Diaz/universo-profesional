"""Integrations application ports."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Protocol
from uuid import UUID

from src.integrations.domain.external_account import ExternalAccount


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


class ImportSessionRepository(Protocol):
    async def create(
        self, *, user_id: UUID, source: str, parsed: dict[str, Any]
    ) -> UUID: ...
    async def get(self, user_id: UUID, session_id: UUID) -> dict[str, Any] | None: ...
    async def mark_committed(self, session_id: UUID) -> None: ...
