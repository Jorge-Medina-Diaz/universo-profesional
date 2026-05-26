"""Universe aggregate — 1:1 with User. Holds top-level profile metadata."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import ClassVar
from uuid import UUID

from src.shared.events import DomainEvent


@dataclass(frozen=True, kw_only=True)
class UniverseCreated(DomainEvent):
    event_type: ClassVar[str] = "universe.created"


@dataclass(frozen=True, kw_only=True)
class UniverseUpdated(DomainEvent):
    event_type: ClassVar[str] = "universe.updated"


@dataclass
class Universe:
    user_id: UUID
    headline: str | None = None
    summary: str | None = None
    photo_url: str | None = None
    current_status: str | None = None  # open_to_offers | searching_actively | not_available
    last_reviewed_at: datetime | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    _events: list[DomainEvent] = field(default_factory=list, repr=False, compare=False)

    @classmethod
    def for_user(cls, user_id: UUID) -> Universe:
        u = cls(user_id=user_id)
        u._events.append(UniverseCreated(user_id=user_id))
        return u

    def update(
        self,
        *,
        headline: str | None = ...,  # type: ignore[assignment]
        summary: str | None = ...,  # type: ignore[assignment]
        photo_url: str | None = ...,  # type: ignore[assignment]
        current_status: str | None = ...,  # type: ignore[assignment]
        now: datetime,
    ) -> None:
        if headline is not ...:
            self.headline = headline
        if summary is not ...:
            self.summary = summary
        if photo_url is not ...:
            self.photo_url = photo_url
        if current_status is not ...:
            self.current_status = current_status
        self.updated_at = now
        self._events.append(UniverseUpdated(user_id=self.user_id))

    def mark_reviewed(self, *, now: datetime) -> None:
        self.last_reviewed_at = now
        self.updated_at = now

    def pop_events(self) -> list[DomainEvent]:
        out = list(self._events)
        self._events.clear()
        return out
