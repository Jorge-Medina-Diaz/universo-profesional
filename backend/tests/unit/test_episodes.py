"""Unit tests for graph episode helpers."""
from __future__ import annotations

from uuid import UUID, uuid4

from src.graph.application.episodes import _episode_uuid_for, _now_iso


class TestEpisodeUuidFor:
    def test_deterministic(self):
        uid = uuid4()
        eid1 = _episode_uuid_for(uid, "sess-1")
        eid2 = _episode_uuid_for(uid, "sess-1")
        assert eid1 == eid2
        assert isinstance(eid1, UUID)

    def test_different_sessions(self):
        uid = uuid4()
        eid1 = _episode_uuid_for(uid, "sess-1")
        eid2 = _episode_uuid_for(uid, "sess-2")
        assert eid1 != eid2

    def test_different_users(self):
        eid1 = _episode_uuid_for(uuid4(), "sess-1")
        eid2 = _episode_uuid_for(uuid4(), "sess-1")
        assert eid1 != eid2


class TestNowIso:
    def test_returns_string(self):
        assert isinstance(_now_iso(), str)
