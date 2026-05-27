from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.graph.application.retrieval._base import ScoredItem


def _attach_ranks(items: list[ScoredItem], *, lane: str) -> list[ScoredItem]:
    for rank, item in enumerate(items, start=1):
        item.rank = rank
        item.lane = lane
    return items


# Cache of (table_name, column_name) -> exists. Populated lazily on first
# query; valid for the process lifetime since schemas only change via
# Alembic migrations that restart the workers anyway.
_COLUMN_EXISTS_CACHE: dict[tuple[str, str], bool] = {}


async def _table_has_column(
    session: AsyncSession, table: str, column: str
) -> bool:
    cache_key = (table, column)
    cached = _COLUMN_EXISTS_CACHE.get(cache_key)
    if cached is not None:
        return cached
    row = (
        await session.execute(
            text(
                "SELECT 1 FROM information_schema.columns "
                "WHERE table_schema = 'public' "
                "  AND table_name = :t AND column_name = :c"
            ),
            {"t": table, "c": column},
        )
    ).first()
    exists = row is not None
    _COLUMN_EXISTS_CACHE[cache_key] = exists
    return exists


def _strip_quotes(value: Any) -> str:
    if value is None:
        return ""
    s = str(value)
    return s.strip('"')


def _coerce_uuid(value: Any) -> UUID | None:
    if value is None:
        return None
    try:
        return UUID(_strip_quotes(value))
    except (ValueError, TypeError):
        return None
