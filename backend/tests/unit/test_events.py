"""Unit tests for shared events."""
from __future__ import annotations

import asyncio
from uuid import uuid4

import pytest

from src.shared.events import DomainEvent, EventBus, get_event_bus, reset_event_bus


class TestDomainEvent:
    def test_to_payload(self):
        e = DomainEvent(user_id=uuid4())
        payload = e.to_payload()
        assert payload["event_type"] == "domain.event"
        assert payload["user_id"] == str(e.user_id)
        assert "event_id" in payload
        assert "occurred_at" in payload


class TestEventBus:
    def test_subscribe_and_publish(self):
        reset_event_bus()
        bus = get_event_bus()
        called = []

        async def handler(event):
            called.append(event)

        bus.subscribe("domain.event", handler)
        evt = DomainEvent()
        asyncio.run(bus.publish(evt))
        assert len(called) == 1

    def test_publish_no_handlers(self):
        reset_event_bus()
        bus = get_event_bus()
        evt = DomainEvent()
        asyncio.run(bus.publish(evt))

    def test_publish_all(self):
        reset_event_bus()
        bus = get_event_bus()
        called = []

        async def handler(event):
            called.append(event)

        bus.subscribe("domain.event", handler)
        asyncio.run(bus.publish_all([DomainEvent(), DomainEvent()]))
        assert len(called) == 2

    def test_safe_invoke_isolates_errors(self):
        reset_event_bus()
        bus = get_event_bus()
        good_called = []

        async def bad_handler(event):
            raise ValueError("boom")

        async def good_handler(event):
            good_called.append(event)

        bus.subscribe("domain.event", bad_handler)
        bus.subscribe("domain.event", good_handler)
        evt = DomainEvent()
        asyncio.run(bus.publish(evt))
        assert len(good_called) == 1
