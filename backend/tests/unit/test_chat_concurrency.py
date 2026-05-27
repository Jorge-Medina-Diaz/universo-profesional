"""Per-user concurrent-stream guard for the /agui chat endpoints.

The guard is an in-memory counter that caps how many simultaneous SSE
streams one user can hold open, so a single client can't exhaust the DB
pool. These tests exercise it directly (no DB / no LLM).
"""
from __future__ import annotations

import pytest
from src.agents.interfaces import agui_router as ar


@pytest.fixture(autouse=True)
def _reset_stream_state():
    ar._active_streams.clear()
    yield
    ar._active_streams.clear()


@pytest.mark.asyncio
async def test_acquire_up_to_max_then_rejects() -> None:
    uid = "user-a"
    cap = ar._MAX_CONCURRENT_STREAMS_PER_USER
    # Up to the cap succeeds.
    for _ in range(cap):
        assert await ar._acquire_stream_slot(uid) is True
    # One more is rejected.
    assert await ar._acquire_stream_slot(uid) is False
    assert ar._active_streams[uid] == cap


@pytest.mark.asyncio
async def test_release_frees_a_slot() -> None:
    uid = "user-b"
    cap = ar._MAX_CONCURRENT_STREAMS_PER_USER
    for _ in range(cap):
        await ar._acquire_stream_slot(uid)
    assert await ar._acquire_stream_slot(uid) is False
    await ar._release_stream_slot(uid)
    # A freed slot can be re-acquired.
    assert await ar._acquire_stream_slot(uid) is True


@pytest.mark.asyncio
async def test_release_to_zero_removes_key() -> None:
    uid = "user-c"
    await ar._acquire_stream_slot(uid)
    await ar._release_stream_slot(uid)
    # No leftover entry once the count hits zero.
    assert uid not in ar._active_streams


@pytest.mark.asyncio
async def test_users_are_independent() -> None:
    cap = ar._MAX_CONCURRENT_STREAMS_PER_USER
    for _ in range(cap):
        await ar._acquire_stream_slot("user-d")
    # A different user is unaffected by another user's saturation.
    assert await ar._acquire_stream_slot("user-e") is True
    assert await ar._acquire_stream_slot("user-d") is False


@pytest.mark.asyncio
async def test_release_when_absent_is_safe() -> None:
    # Releasing a slot that was never acquired must not raise or go negative.
    await ar._release_stream_slot("ghost")
    assert "ghost" not in ar._active_streams
