"""SQLAlchemy implementations of integrations ports."""
from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import delete, desc, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.integrations.application.ports import (
    ExternalAccountRepository,
    ImportSessionRepository,
    SyncRunsRepository,
)
from src.integrations.domain.external_account import ExternalAccount
from src.integrations.infrastructure.orm import (
    ExternalAccountOrm,
    ImportSessionOrm,
    IntegrationSyncRunOrm,
)
from src.shared.fernet import decrypt, encrypt
from src.shared.security import utc_now


def _to_domain(row: ExternalAccountOrm) -> ExternalAccount:
    return ExternalAccount(
        id=row.id,
        user_id=row.user_id,
        provider=row.provider,
        provider_user_id=row.provider_user_id,
        provider_username=row.provider_username,
        access_token=decrypt(row.access_token_encrypted) if row.access_token_encrypted else None,
        refresh_token=decrypt(row.refresh_token_encrypted) if row.refresh_token_encrypted else None,
        expires_at=row.expires_at,
        scopes=list(row.scopes or []),
        metadata=dict(row.extra_metadata or {}),
        connected_at=row.connected_at,
        last_synced_at=row.last_synced_at,
        sync_status=row.sync_status,
        sync_error=row.sync_error,
    )


class SqlExternalAccountRepository(ExternalAccountRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, user_id: UUID, provider: str) -> ExternalAccount | None:
        stmt = (
            select(ExternalAccountOrm)
            .where(ExternalAccountOrm.user_id == user_id)
            .where(ExternalAccountOrm.provider == provider)
        )
        row = (await self._session.execute(stmt)).scalar_one_or_none()
        return _to_domain(row) if row else None

    async def list_for_user(self, user_id: UUID) -> list[ExternalAccount]:
        stmt = select(ExternalAccountOrm).where(ExternalAccountOrm.user_id == user_id)
        rows = (await self._session.execute(stmt)).scalars().all()
        return [_to_domain(r) for r in rows]

    async def upsert(self, account: ExternalAccount) -> None:
        existing = (
            await self._session.execute(
                select(ExternalAccountOrm)
                .where(ExternalAccountOrm.user_id == account.user_id)
                .where(ExternalAccountOrm.provider == account.provider)
            )
        ).scalar_one_or_none()
        if existing is None:
            self._session.add(
                ExternalAccountOrm(
                    id=account.id,
                    user_id=account.user_id,
                    provider=account.provider,
                    provider_user_id=account.provider_user_id,
                    provider_username=account.provider_username,
                    access_token_encrypted=(
                        encrypt(account.access_token) if account.access_token else None
                    ),
                    refresh_token_encrypted=(
                        encrypt(account.refresh_token) if account.refresh_token else None
                    ),
                    expires_at=account.expires_at,
                    scopes=account.scopes,
                    extra_metadata=account.metadata,
                    connected_at=account.connected_at,
                    last_synced_at=account.last_synced_at,
                    sync_status=account.sync_status,
                    sync_error=account.sync_error,
                )
            )
        else:
            existing.provider_user_id = account.provider_user_id
            existing.provider_username = account.provider_username
            if account.access_token:
                existing.access_token_encrypted = encrypt(account.access_token)
            if account.refresh_token is not None:
                existing.refresh_token_encrypted = (
                    encrypt(account.refresh_token) if account.refresh_token else None
                )
            existing.expires_at = account.expires_at
            existing.scopes = account.scopes
            existing.extra_metadata = account.metadata
            existing.last_synced_at = account.last_synced_at
            existing.sync_status = account.sync_status
            existing.sync_error = account.sync_error
        await self._session.flush()

    async def delete(self, user_id: UUID, provider: str) -> bool:
        stmt = (
            delete(ExternalAccountOrm)
            .where(ExternalAccountOrm.user_id == user_id)
            .where(ExternalAccountOrm.provider == provider)
            .returning(ExternalAccountOrm.id)
        )
        result = await self._session.execute(stmt)
        return result.first() is not None

    async def touch_sync(
        self,
        user_id: UUID,
        provider: str,
        *,
        ok: bool,
        error: str | None,
        when: datetime,
    ) -> None:
        stmt = (
            update(ExternalAccountOrm)
            .where(ExternalAccountOrm.user_id == user_id)
            .where(ExternalAccountOrm.provider == provider)
            .values(
                last_synced_at=when,
                sync_status="ok" if ok else "error",
                sync_error=error,
            )
        )
        await self._session.execute(stmt)
        await self._session.flush()


class SqlSyncRunsRepository(SyncRunsRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def start(self, user_id: UUID, provider: str) -> UUID:
        run_id = uuid4()
        self._session.add(
            IntegrationSyncRunOrm(
                id=run_id,
                user_id=user_id,
                provider=provider,
                started_at=utc_now(),
            )
        )
        await self._session.flush()
        return run_id

    async def finish(
        self,
        run_id: UUID,
        *,
        ok: bool,
        items_created: int,
        items_updated: int,
        error: str | None,
        summary: dict[str, Any] | None,
    ) -> None:
        stmt = (
            update(IntegrationSyncRunOrm)
            .where(IntegrationSyncRunOrm.id == run_id)
            .values(
                finished_at=utc_now(),
                ok=ok,
                items_created=items_created,
                items_updated=items_updated,
                error=error,
                summary=summary,
            )
        )
        await self._session.execute(stmt)
        await self._session.flush()

    async def list_for_user(self, user_id: UUID, limit: int = 10) -> list[dict[str, Any]]:
        stmt = (
            select(IntegrationSyncRunOrm)
            .where(IntegrationSyncRunOrm.user_id == user_id)
            .order_by(desc(IntegrationSyncRunOrm.started_at))
            .limit(limit * 2)  # over-fetch to account for cancelled-dismissed rows
        )
        rows = (await self._session.execute(stmt)).scalars().all()
        out: list[dict[str, Any]] = []
        for r in rows:
            summary = r.summary or {}
            # Cancel-dismiss is a soft flag we stamp in `summary._cancelled_requested_at`.
            # Hidden rows still exist in the DB for audit but disappear from the UI tray.
            if isinstance(summary, dict) and summary.get("_cancelled_requested_at"):
                continue
            out.append(
                {
                    "id": str(r.id),
                    "provider": r.provider,
                    "started_at": r.started_at.isoformat(),
                    "finished_at": r.finished_at.isoformat() if r.finished_at else None,
                    "ok": r.ok,
                    "items_created": r.items_created,
                    "items_updated": r.items_updated,
                    "error": r.error,
                    "summary": summary,
                }
            )
            if len(out) >= limit:
                break
        return out

    async def is_cancelled(self, run_id: UUID) -> bool:
        """Return True if a soft-cancel has been requested for this run.

        Reads `summary._cancelled_requested_at` written by `request_cancel`
        in a parallel transaction (the cancel endpoint). We bypass the
        SQLAlchemy identity map with `populate_existing=True` because the
        row was inserted earlier in *this* session by `start()` and would
        otherwise be served stale from the cache.
        """
        stmt = (
            select(IntegrationSyncRunOrm.summary)
            .where(IntegrationSyncRunOrm.id == run_id)
            .execution_options(populate_existing=True)
        )
        row = (await self._session.execute(stmt)).first()
        if row is None:
            return False
        summary = row[0] or {}
        if not isinstance(summary, dict):
            return False
        return bool(summary.get("_cancelled_requested_at"))

    async def request_cancel(self, run_id: UUID, user_id: UUID) -> bool:
        """Mark a sync run as cancel-requested. Returns False if not found.

        Sprint F: this is a *soft* cancel. The flag is persisted to
        `summary._cancelled_requested_at` so the row stays out of the user's
        tray, and future sync implementations can poll for it to abort
        mid-flight. The current sync code does NOT honour it — runs in
        progress will still complete in the background.
        """
        from datetime import datetime

        stmt = select(IntegrationSyncRunOrm).where(
            IntegrationSyncRunOrm.id == run_id,
            IntegrationSyncRunOrm.user_id == user_id,
        )
        row = (await self._session.execute(stmt)).scalar_one_or_none()
        if row is None:
            return False
        summary = dict(row.summary or {})
        if not summary.get("_cancelled_requested_at"):
            summary["_cancelled_requested_at"] = datetime.now(UTC).isoformat()
            row.summary = summary
        return True


class SqlImportSessionRepository(ImportSessionRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, *, user_id: UUID, source: str, parsed: dict[str, Any]) -> UUID:
        sid = uuid4()
        self._session.add(
            ImportSessionOrm(
                id=sid,
                user_id=user_id,
                source=source,
                status="parsed",
                parsed=parsed,
                created_at=utc_now(),
            )
        )
        await self._session.flush()
        return sid

    async def get(self, user_id: UUID, session_id: UUID) -> dict[str, Any] | None:
        stmt = (
            select(ImportSessionOrm)
            .where(ImportSessionOrm.id == session_id)
            .where(ImportSessionOrm.user_id == user_id)
        )
        row = (await self._session.execute(stmt)).scalar_one_or_none()
        if row is None:
            return None
        return {
            "id": str(row.id),
            "source": row.source,
            "status": row.status,
            "parsed": row.parsed,
            "created_at": row.created_at.isoformat(),
            "committed_at": row.committed_at.isoformat() if row.committed_at else None,
        }

    async def mark_committed(self, session_id: UUID) -> None:
        stmt = (
            update(ImportSessionOrm)
            .where(ImportSessionOrm.id == session_id)
            .values(status="committed", committed_at=utc_now())
        )
        await self._session.execute(stmt)
        await self._session.flush()
