"""Thin helper that wraps an asyncpg connection for LISTEN/NOTIFY."""
from __future__ import annotations

import asyncio
from typing import Any


class PgListener:
    def __init__(self, conn: Any) -> None:
        self._conn = conn
        self._queue: asyncio.Queue[str] = asyncio.Queue()
        self._conn.add_listener("entity_changed", self._on_notify)

    def _on_notify(self, connection: Any, pid: int, channel: str, payload: str) -> None:
        self._queue.put_nowait(payload or "")

    async def get(self, wait_for: float | None = None) -> str | None:
        try:
            return await asyncio.wait_for(self._queue.get(), timeout=wait_for)
        except TimeoutError:
            return None
