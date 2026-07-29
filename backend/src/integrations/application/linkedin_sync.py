"""LinkedIn sync use cases.

Wraps both DMA and Bright Data providers behind a single 'fetch + open import
session' flow. The session_id returned can then be committed selectively just
like ZIP/PDF imports — same UX, same MCP tools.

Two entry points:
  * SyncLinkedinDma — uses the DMA provider; requires the DMA OAuth scope to
    have been granted (which we do via the dedicated DMA authorize flow).
  * SyncLinkedinBrightdata — uses Bright Data's LinkedIn People Profile API;
    requires PRO tier (enforced at the router via `require_pro_tier`) plus a
    public LinkedIn URL (auto-resolved from OIDC metadata when not provided).
"""
from __future__ import annotations

import asyncio
import contextlib
from typing import Any
from uuid import UUID

import structlog

from src.integrations.application.linkedin_brightdata_sync import (
    BrightDataLinkedInProvider,
)
from src.integrations.application.linkedin_dma_sync import DmaLinkedInProvider
from src.integrations.application.linkedin_mapper import profile_to_universe_payloads
from src.integrations.application.ports import (
    ExternalAccountRepository,
    ImportSessionRepository,
    OperationCancelledError,
    SyncRunsRepository,
)
from src.shared.security import utc_now
from src.shared.uow import UnitOfWork

logger = structlog.get_logger(__name__)


async def _run_with_cooperative_cancel(
    coro,
    *,
    runs: SyncRunsRepository,
    run_id: UUID,
    poll_seconds: float = 2.0,
    stage: str = "fetch_mid_flight",
):
    """Run `coro` as a Task and poll for cancellation every `poll_seconds`.

    Uses `asyncio.shield + wait_for(timeout)` so the outer wait can timeout
    without cancelling the underlying task. If the cancel flag fires, we
    explicitly cancel the task, swallow whatever it raises, and propagate
    `OperationCancelledError` so the use case's except handler picks it up.

    This lets us bail out of a long blocking HTTP call (Bright Data scrape
    polling for 30-90s) at any point — not only before/after it.
    """
    task = asyncio.create_task(coro)
    while True:
        try:
            return await asyncio.wait_for(asyncio.shield(task), timeout=poll_seconds)
        except TimeoutError:
            if await runs.is_cancelled(run_id):
                task.cancel()
                with contextlib.suppress(asyncio.CancelledError, Exception):
                    await task
                # `from None`: the TimeoutError is just our polling tick, not
                # the reason the operation stopped — the user cancelling is.
                raise OperationCancelledError(stage) from None
            # Not cancelled yet — keep waiting.
            continue


class SyncLinkedinDma:
    def __init__(
        self,
        accounts: ExternalAccountRepository,
        sessions: ImportSessionRepository,
        runs: SyncRunsRepository,
    ) -> None:
        self._accounts = accounts
        self._sessions = sessions
        self._runs = runs

    async def execute(self, *, user_id: str, uow: UnitOfWork) -> dict[str, Any]:
        uid = UUID(user_id)
        run_id = await self._runs.start(uid, "linkedin_dma")
        # DMA token is stored under provider="linkedin_dma" (separate from OIDC)
        account = await self._accounts.get(uid, "linkedin_dma")
        try:
            provider = DmaLinkedInProvider()
            profile = await provider.fetch_profile(user_id=uid, account=account)
            # Cooperative cancel right after the HTTP fetch — the network call
            # can't be aborted mid-flight but the user can still bail before
            # we commit the parsed payload into an import_session.
            if await self._runs.is_cancelled(run_id):
                raise OperationCancelledError("post_fetch")
            parsed = profile_to_universe_payloads(profile)
            sid = await self._sessions.create(
                user_id=uid, source="linkedin_dma", parsed=parsed
            )
            now = utc_now()
            await self._accounts.touch_sync(
                uid, "linkedin_dma", ok=True, error=None, when=now
            )
            counts = {k: len(v) for k, v in parsed.items() if isinstance(v, list)}
            await self._runs.finish(
                run_id,
                ok=True,
                items_created=0,  # not yet — commit step does that
                items_updated=0,
                error=None,
                summary={
                    "session_id": str(sid),
                    "parsed_counts": counts,
                    "fixture_used": parsed.get("basics", {}).get("source_metadata", {})
                    if isinstance(parsed.get("basics"), dict)
                    else None,
                },
            )
            return {"session_id": str(sid), "parsed": parsed}
        except OperationCancelledError as exc:
            logger.info("linkedin_dma_sync_cancelled", stage=str(exc))
            await self._accounts.touch_sync(
                uid, "linkedin_dma", ok=False, error="cancelled", when=utc_now()
            )
            await self._runs.finish(
                run_id,
                ok=False,
                items_created=0,
                items_updated=0,
                error="cancelled",
                summary={"cancelled_stage": str(exc)},
            )
            return {"ok": False, "error": "cancelled"}
        except Exception as exc:
            logger.exception("linkedin_dma_sync_failed", error=str(exc))
            await self._accounts.touch_sync(
                uid, "linkedin_dma", ok=False, error=str(exc), when=utc_now()
            )
            await self._runs.finish(
                run_id,
                ok=False,
                items_created=0,
                items_updated=0,
                error=str(exc),
                summary=None,
            )
            return {"ok": False, "error": str(exc)}


class SyncLinkedinBrightdata:
    def __init__(
        self,
        accounts: ExternalAccountRepository,
        sessions: ImportSessionRepository,
        runs: SyncRunsRepository,
    ) -> None:
        self._accounts = accounts
        self._sessions = sessions
        self._runs = runs

    async def execute(
        self,
        *,
        user_id: str,
        linkedin_url: str | None,
        fresh: bool,
        uow: UnitOfWork,
    ) -> dict[str, Any]:
        uid = UUID(user_id)
        run_id = await self._runs.start(uid, "linkedin_brightdata")
        # If we don't have a URL, try the OIDC account's stored profile URL
        account = await self._accounts.get(uid, "linkedin_oidc")
        try:
            provider = BrightDataLinkedInProvider()
            # Bright Data is the slowest sync (30-90s polling their async API).
            # Wrap the fetch in a Task with cooperative cancel: we poll our
            # cancel flag every 2s and abort the in-flight HTTP if requested.
            profile = await _run_with_cooperative_cancel(
                provider.fetch_profile(
                    user_id=uid,
                    account=account,
                    linkedin_url=linkedin_url,
                    fresh=fresh,
                ),
                runs=self._runs,
                run_id=run_id,
                stage="brightdata_fetch",
            )
            # Belt-and-braces post-fetch check (race between resolve + commit).
            if await self._runs.is_cancelled(run_id):
                raise OperationCancelledError("post_fetch")
            parsed = profile_to_universe_payloads(profile)
            sid = await self._sessions.create(
                user_id=uid, source="linkedin_brightdata", parsed=parsed
            )
            counts = {k: len(v) for k, v in parsed.items() if isinstance(v, list)}
            await self._runs.finish(
                run_id,
                ok=True,
                items_created=0,
                items_updated=0,
                error=None,
                summary={
                    "session_id": str(sid),
                    "parsed_counts": counts,
                    "linkedin_url": linkedin_url,
                    "fresh": fresh,
                },
            )
            return {"session_id": str(sid), "parsed": parsed}
        except OperationCancelledError as exc:
            logger.info("linkedin_brightdata_sync_cancelled", stage=str(exc))
            await self._runs.finish(
                run_id,
                ok=False,
                items_created=0,
                items_updated=0,
                error="cancelled",
                summary={
                    "linkedin_url": linkedin_url,
                    "cancelled_stage": str(exc),
                },
            )
            return {"ok": False, "error": "cancelled"}
        except Exception as exc:
            logger.exception("linkedin_brightdata_sync_failed", error=str(exc))
            await self._runs.finish(
                run_id,
                ok=False,
                items_created=0,
                items_updated=0,
                error=str(exc),
                summary={"linkedin_url": linkedin_url},
            )
            return {"ok": False, "error": str(exc)}
