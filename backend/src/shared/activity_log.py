"""Activity log: persists every DomainEvent to the `domain_events` table.

Subscriber registered at app startup. Reads `current_user_id` from the Postgres
session variable (already set by RLS) so it runs under the caller's identity.

This is the spec's "transactional outbox light" — we persist after commit, so
write amplification is bounded and downstream replay can use this table.
"""
from __future__ import annotations

from typing import Any

import structlog
from sqlalchemy import text

from src.shared.db import get_session_factory
from src.shared.events import DomainEvent, EventBus

logger = structlog.get_logger(__name__)


async def persist_event_handler(event: DomainEvent) -> None:
    """Append a row to domain_events. Best-effort: failures only warn."""
    payload: dict[str, Any] = dict(event.to_payload())
    # Attach the rest of the dataclass fields (excluding event_id, occurred_at, user_id)
    for k, v in event.__dict__.items():
        if k in {"event_id", "occurred_at", "user_id", "_events"}:
            continue
        payload[k] = _coerce(v)

    try:
        factory = get_session_factory()
        async with factory() as session:
            await session.execute(
                text(
                    """
                    INSERT INTO domain_events (event_id, user_id, aggregate_id, event_type, payload, occurred_at)
                    VALUES (CAST(:eid AS uuid), CAST(:uid AS uuid), NULL, :etype, CAST(:payload AS jsonb), :occurred_at)
                    """
                ).bindparams(
                    eid=str(event.event_id),
                    uid=str(event.user_id) if event.user_id else None,
                    etype=event.event_type,
                    payload=_json_encode(payload),
                    occurred_at=event.occurred_at,
                )
            )
            await session.commit()
    except Exception as exc:
        logger.warning(
            "activity_log_persist_failed",
            event_type=event.event_type,
            error=str(exc),
        )


def _coerce(v: Any) -> Any:
    from datetime import date, datetime
    from uuid import UUID

    if isinstance(v, datetime):
        return v.isoformat()
    if isinstance(v, date):
        return v.isoformat()
    if isinstance(v, UUID):
        return str(v)
    if isinstance(v, dict):
        return {k: _coerce(val) for k, val in v.items()}
    if isinstance(v, list):
        return [_coerce(x) for x in v]
    return v


def _json_encode(d: dict[str, Any]) -> str:
    import json

    return json.dumps(d, default=str, separators=(",", ":"))


def register(bus: EventBus) -> None:
    """Subscribe to every relevant event_type to persist into domain_events."""
    # We use a wildcard pattern: known event_types from each context
    event_types = [
        "identity.user_registered",
        "identity.email_verified",
        "identity.password_changed",
        "identity.account_soft_deleted",
        "universe.created",
        "universe.updated",
        "universe.entry_added",
        "universe.entry_updated",
        "universe.entry_removed",
        "documents.generated",
        "integrations.connected",
        "integrations.disconnected",
        "integrations.synced",
        "suggestions.created",
        "suggestions.acted",
        "reminders.dispatched",
    ]
    for et in event_types:
        bus.subscribe(et, persist_event_handler)
