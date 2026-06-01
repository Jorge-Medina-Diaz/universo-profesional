"""Cursor-based (keyset) pagination primitive — shared kernel.

Append-only feeds (activity, change log) must not return unbounded result sets,
and must not skip or duplicate rows when many share a timestamp. We page by a
STABLE composite key (timestamp, id) encoded in an opaque base64 cursor — never
a raw OFFSET. Layer-agnostic (pydantic-free) so any layer may import it.

Wire a query for keyset paging by:
  1. accepting an opaque `cursor`; decode_cursor() -> (ts, id) or None,
  2. fetching `limit + 1` rows ordered by (ts DESC, id DESC), adding
     `WHERE (ts, id) < (:c_ts, :c_id)` when a cursor is present,
  3. returning build_page(rows, limit, ts_key=..., id_key=...).
"""
from __future__ import annotations

import base64
import binascii
import json
from datetime import datetime
from typing import Any
from uuid import UUID


def encode_cursor(ts: Any, row_id: Any) -> str:
    """Opaque base64 of [iso_timestamp, id]."""
    ts_str = ts.isoformat() if hasattr(ts, "isoformat") else str(ts)
    raw = json.dumps([ts_str, str(row_id)], separators=(",", ":"))
    return base64.urlsafe_b64encode(raw.encode()).decode()


def decode_cursor(cursor: str | None) -> tuple[str, str] | None:
    """Return (timestamp, id) from a cursor, or None if absent/malformed.

    A malformed cursor is treated as 'first page' (None), never an error — the
    cursor is opaque client state, so we degrade gracefully rather than 500.
    """
    if not cursor:
        return None
    try:
        raw = base64.urlsafe_b64decode(cursor.encode()).decode()
        ts_str, row_id = json.loads(raw)
        # Validate the decoded values too: a structurally-valid but semantically
        # garbage cursor (e.g. ["nope", "nope"]) must degrade to "first page",
        # not 500 later in the SQL ::timestamptz / ::uuid cast.
        datetime.fromisoformat(str(ts_str))
        UUID(str(row_id))
        return str(ts_str), str(row_id)
    except (binascii.Error, ValueError, TypeError):
        return None


def build_page(
    rows: list[dict[str, Any]], limit: int, *, ts_key: str, id_key: str
) -> dict[str, Any]:
    """Trim a `limit + 1` fetch down to `limit` and mint next_cursor from the
    last kept row. Returns {"items": [...], "next_cursor": str | None}."""
    has_more = len(rows) > limit
    items = rows[:limit]
    next_cursor = (
        encode_cursor(items[-1][ts_key], items[-1][id_key])
        if has_more and items
        else None
    )
    return {"items": items, "next_cursor": next_cursor}
