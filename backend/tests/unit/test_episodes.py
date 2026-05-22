"""Smoke tests for episode id derivation (pure, no DB).

Protects the Sprint-cleanup critical fix: the Episode vertex id must
include the user_id so two users with a colliding chat_session_id never
land on the same Episode node.
"""
from __future__ import annotations

from uuid import UUID, uuid4

from src.graph.application.episodes import _episode_uuid_for


def test_is_deterministic() -> None:
    uid = uuid4()
    a = _episode_uuid_for(uid, "session-abc")
    b = _episode_uuid_for(uid, "session-abc")
    assert a == b


def test_returns_uuid() -> None:
    assert isinstance(_episode_uuid_for(uuid4(), "s"), UUID)


def test_disjoint_across_users_same_session() -> None:
    u1, u2 = uuid4(), uuid4()
    assert _episode_uuid_for(u1, "shared-session") != _episode_uuid_for(
        u2, "shared-session"
    )


def test_disjoint_across_sessions_same_user() -> None:
    uid = uuid4()
    assert _episode_uuid_for(uid, "s1") != _episode_uuid_for(uid, "s2")
