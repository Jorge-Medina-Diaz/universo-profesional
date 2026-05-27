"""Unit tests for Universe aggregate."""
from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from src.universe.domain.universe import Universe, UniverseCreated, UniverseUpdated


class TestUniverse:
    def test_for_user_emits_created_event(self):
        uid = uuid4()
        u = Universe.for_user(uid)
        assert u.user_id == uid
        events = u.pop_events()
        assert len(events) == 1
        assert isinstance(events[0], UniverseCreated)

    def test_update_sets_fields(self):
        uid = uuid4()
        u = Universe.for_user(uid)
        u.pop_events()
        now = datetime.now(UTC)
        u.update(headline="Dev", now=now)
        assert u.headline == "Dev"
        assert u.updated_at == now
        events = u.pop_events()
        assert len(events) == 1
        assert isinstance(events[0], UniverseUpdated)

    def test_update_multiple_fields(self):
        uid = uuid4()
        u = Universe.for_user(uid)
        u.pop_events()
        now = datetime.now(UTC)
        u.update(headline="H", summary="S", photo_url="https://x.com", current_status="open", now=now)
        assert u.headline == "H"
        assert u.summary == "S"
        assert u.photo_url == "https://x.com"
        assert u.current_status == "open"

    def test_update_does_not_touch_unset_fields(self):
        uid = uuid4()
        u = Universe.for_user(uid)
        u.headline = "Existing"
        u.pop_events()
        now = datetime.now(UTC)
        u.update(summary="New", now=now)
        assert u.headline == "Existing"
        assert u.summary == "New"

    def test_mark_reviewed(self):
        uid = uuid4()
        u = Universe.for_user(uid)
        now = datetime.now(UTC)
        u.mark_reviewed(now=now)
        assert u.last_reviewed_at == now
        assert u.updated_at == now

    def test_pop_events_clears_list(self):
        uid = uuid4()
        u = Universe.for_user(uid)
        first = u.pop_events()
        second = u.pop_events()
        assert len(first) == 1
        assert len(second) == 0
