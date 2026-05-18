"""Unit of Work abstraction over SQLAlchemy AsyncSession.

The UoW collects domain events emitted by aggregates during the transaction
and dispatches them to the EventBus *after commit*. This gives us the
"transactional outbox light" semantics needed for embedding refresh and
audit logging without a separate outbox table.
"""
from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Self

from sqlalchemy.ext.asyncio import AsyncSession

from .events import DomainEvent, get_event_bus


class UnitOfWork:
    """One unit of work == one DB transaction + post-commit event dispatch."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self._pending_events: list[DomainEvent] = []
        self._committed = False

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(self, exc_type: object, exc: object, tb: object) -> None:
        if exc_type is not None:
            await self.session.rollback()
            return
        if not self._committed:
            await self.session.rollback()

    def add_event(self, event: DomainEvent) -> None:
        self._pending_events.append(event)

    def add_events(self, events: list[DomainEvent]) -> None:
        self._pending_events.extend(events)

    async def commit(self) -> None:
        await self.session.commit()
        self._committed = True
        # Dispatch after commit so subscribers see persisted state
        bus = get_event_bus()
        events_to_dispatch = self._pending_events
        self._pending_events = []
        await bus.publish_all(events_to_dispatch)

    async def rollback(self) -> None:
        await self.session.rollback()
        self._pending_events.clear()


@asynccontextmanager
async def unit_of_work(session: AsyncSession) -> AsyncIterator[UnitOfWork]:
    uow = UnitOfWork(session)
    async with uow:
        yield uow
