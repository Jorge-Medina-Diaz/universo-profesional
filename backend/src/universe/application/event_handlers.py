"""Event subscribers for the Universe context."""
from __future__ import annotations

import structlog

from src.shared.events import DomainEvent, EventBus
from src.universe.domain.entities import EntryAdded, EntryUpdated

logger = structlog.get_logger(__name__)


async def on_entry_added(event: DomainEvent) -> None:
    if not isinstance(event, EntryAdded):
        return
    logger.info(
        "entry_added",
        entity_type=event.entity_type,
        entity_id=event.entity_id_str,
        user_id=str(event.user_id) if event.user_id else None,
    )


async def on_entry_updated(event: DomainEvent) -> None:
    if not isinstance(event, EntryUpdated):
        return
    logger.info(
        "entry_updated",
        entity_type=event.entity_type,
        entity_id=event.entity_id_str,
        user_id=str(event.user_id) if event.user_id else None,
    )


def register_universe_subscribers(bus: EventBus) -> None:
    bus.subscribe(EntryAdded.event_type, on_entry_added)
    bus.subscribe(EntryUpdated.event_type, on_entry_updated)
