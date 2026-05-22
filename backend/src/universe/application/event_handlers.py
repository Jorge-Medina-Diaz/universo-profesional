"""Event subscribers for the Universe context."""
from __future__ import annotations

import asyncio
from uuid import UUID

import structlog

from src.shared.events import DomainEvent, EventBus
from src.universe.domain.entities import EntryAdded, EntryRemoved, EntryUpdated

logger = structlog.get_logger(__name__)


# Entities whose changes invalidate the polyglot shape.
_SHAPE_AFFECTING = {"skill", "project", "experience"}


async def on_entry_added(event: DomainEvent) -> None:
    if not isinstance(event, EntryAdded):
        return
    logger.info(
        "entry_added",
        entity_type=event.entity_type,
        entity_id=event.entity_id_str,
        user_id=str(event.user_id) if event.user_id else None,
    )
    _maybe_schedule_shape_recompute(event.entity_type, event.user_id)


async def on_entry_updated(event: DomainEvent) -> None:
    if not isinstance(event, EntryUpdated):
        return
    logger.info(
        "entry_updated",
        entity_type=event.entity_type,
        entity_id=event.entity_id_str,
        user_id=str(event.user_id) if event.user_id else None,
    )
    _maybe_schedule_shape_recompute(event.entity_type, event.user_id)


async def on_entry_removed(event: DomainEvent) -> None:
    if not isinstance(event, EntryRemoved):
        return
    logger.info(
        "entry_removed",
        entity_type=event.entity_type,
        entity_id=event.entity_id_str,
        user_id=str(event.user_id) if event.user_id else None,
    )
    _maybe_schedule_shape_recompute(event.entity_type, event.user_id)


def _maybe_schedule_shape_recompute(entity_type: str, user_id: UUID | None) -> None:
    if entity_type not in _SHAPE_AFFECTING:
        return
    if user_id is None:
        return
    # Fire-and-forget: caller's request is not blocked.
    try:
        asyncio.get_running_loop().create_task(_recompute_shape_safe(user_id))
    except RuntimeError:
        # No running loop (e.g. sync context) — skip; quarterly recompute via
        # the CLI / scheduled job will catch up.
        logger.debug("shape_recompute_skipped_no_loop", user_id=str(user_id))


async def _recompute_shape_safe(user_id: UUID) -> None:
    from src.shared.db import get_session_factory, set_rls_user
    from src.universe.application.shape_service import compute_area_strengths
    from src.universe.application.signal_extraction import extract_user_signals

    try:
        factory = get_session_factory()
        async with factory() as session:
            await set_rls_user(session, user_id)
            shape_result = await compute_area_strengths(session, user_id)
            # After shape is known, refresh signals for primary areas only —
            # cheaper than scanning the whole corpus and good enough as a
            # signal that the polyglot dimensions changed.
            primary_areas = list(shape_result.primary_areas) or [None]
            for area in primary_areas[:2]:
                await extract_user_signals(session, user_id, sector=area)
            await session.commit()
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "shape_signals_recompute_failed",
            user_id=str(user_id),
            error=str(exc),
        )


def register_universe_subscribers(bus: EventBus) -> None:
    bus.subscribe(EntryAdded.event_type, on_entry_added)
    bus.subscribe(EntryUpdated.event_type, on_entry_updated)
    bus.subscribe(EntryRemoved.event_type, on_entry_removed)
