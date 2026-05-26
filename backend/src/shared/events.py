"""In-process async event bus.

For MVP scope (single-process FastAPI app) this is sufficient. Migrating to
a durable bus (Postgres LISTEN/NOTIFY, NATS, Kafka) is a one-class swap.

Domain events are emitted by aggregates and dispatched by the application
layer after a successful Unit of Work commit ("transactional outbox" pattern
is overkill for MVP; we use post-commit dispatch with at-most-once semantics
for embedding refresh, which is idempotent anyway).
"""
from __future__ import annotations

import asyncio
from collections import defaultdict
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, ClassVar
from uuid import UUID, uuid4

import structlog

logger = structlog.get_logger(__name__)


@dataclass(frozen=True, kw_only=True)
class DomainEvent:
    """Base class for every domain event.

    Subclasses are frozen dataclasses with `kw_only=True` (override fields with
    defaults). Use `event_type` (ClassVar) to override the dispatcher key.
    """

    event_id: UUID = field(default_factory=uuid4)
    occurred_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    user_id: UUID | None = None
    event_type: ClassVar[str] = "domain.event"

    def to_payload(self) -> dict[str, Any]:
        """Serializable payload (for the `domain_events` table or worker queue)."""
        return {
            "event_id": str(self.event_id),
            "event_type": self.event_type,
            "occurred_at": self.occurred_at.isoformat(),
            "user_id": str(self.user_id) if self.user_id else None,
        }


EventHandler = Callable[[DomainEvent], Awaitable[None]]


class EventBus:
    """In-process pub-sub with sequential dispatch and error isolation."""

    def __init__(self) -> None:
        self._handlers: dict[str, list[EventHandler]] = defaultdict(list)

    def subscribe(self, event_type: str, handler: EventHandler) -> None:
        self._handlers[event_type].append(handler)

    async def publish(self, event: DomainEvent) -> None:
        handlers = self._handlers.get(event.event_type, [])
        if not handlers:
            return
        await asyncio.gather(
            *(self._safe_invoke(handler, event) for handler in handlers),
            return_exceptions=False,
        )

    async def publish_all(self, events: list[DomainEvent]) -> None:
        for event in events:
            await self.publish(event)

    async def _safe_invoke(self, handler: EventHandler, event: DomainEvent) -> None:
        try:
            await handler(event)
        except Exception as exc:
            logger.error(
                "event_handler_failed",
                event_type=event.event_type,
                event_id=str(event.event_id),
                handler=handler.__qualname__,
                error=str(exc),
                exc_info=True,
            )


_bus: EventBus | None = None


def get_event_bus() -> EventBus:
    global _bus
    if _bus is None:
        _bus = EventBus()
    return _bus


def reset_event_bus() -> None:
    """Test-only: drop subscriptions between tests."""
    global _bus
    _bus = None
