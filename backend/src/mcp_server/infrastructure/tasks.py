"""Arq tasks + cron for the MCP server lifecycle.

Currently:
  * `purge_expired_oauth_tokens` — daily sweep that removes OAuth tokens
    whose `expires_at` is in the past. Keeps the table size predictable
    and reduces leak surface area (an old token DB row is useless once
    expired, but it's still a row).
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import structlog
from sqlalchemy import delete

from src.mcp_server.infrastructure.orm import OAuthTokenOrm
from src.shared.db import get_session_factory

logger = structlog.get_logger(__name__)


async def purge_expired_oauth_tokens(ctx: dict[str, Any]) -> dict[str, int]:
    """Delete OAuth tokens whose `expires_at` is older than now.

    Runs on a cron schedule (see worker.py). We delete rather than
    soft-delete because once expired the row has zero value — the audit
    log of token activity is in `mcp_invocations` (separate table).
    """
    factory = get_session_factory()
    now = datetime.now(timezone.utc)
    async with factory() as session:
        stmt = delete(OAuthTokenOrm).where(OAuthTokenOrm.expires_at < now)
        result = await session.execute(stmt)
        await session.commit()
        removed = result.rowcount or 0
        logger.info("oauth_tokens_purged", removed=removed)
        return {"removed": removed}
