"""R15 s2: full-graph enrichment is debounced off the chat turn.

enqueue_graph_enrichment must (a) enqueue a per-user coalesced job when the arq
pool is reachable, (b) return True so the caller does NOT run inline, and
(c) return False when the queue is down so the caller CAN fall back to inline —
enrichment must never silently stop. No real Redis here; create_pool is mocked.
"""
from __future__ import annotations

from uuid import UUID

import pytest
from src.universe.infrastructure import scheduler as s

_UID = UUID("11111111-1111-1111-1111-111111111111")


class _FakePool:
    def __init__(self, boom: bool = False, coalesce: bool = False) -> None:
        self.calls: list[tuple[str, dict]] = []
        self._boom = boom
        self._coalesce = coalesce

    async def enqueue_job(self, name, **kw):
        if self._boom:
            raise RuntimeError("redis gone")
        self.calls.append((name, kw))
        # arq returns a Job for a fresh enqueue, or None when a job with the same
        # _job_id already exists (coalesced) — both mean "enrichment is scheduled".
        return None if self._coalesce else object()


@pytest.fixture(autouse=True)
def _reset_pool():
    s._enrichment_pool = None
    yield
    s._enrichment_pool = None


async def test_enqueues_coalesced_per_user_job(monkeypatch):
    fake = _FakePool()

    async def _fake_create_pool(*a, **k):
        return fake

    monkeypatch.setattr(s, "create_pool", _fake_create_pool)
    ok = await s.enqueue_graph_enrichment(_UID)
    assert ok is True
    assert len(fake.calls) == 1
    name, kw = fake.calls[0]
    assert name == "enrich_universe_task"
    assert kw["user_id"] == str(_UID)
    # Fixed per-user job id is what makes rapid turns coalesce into one job.
    assert kw["_job_id"] == f"enrich-graph:{_UID}"
    assert kw["_defer_by"] == 5


async def test_coalesced_enqueue_still_returns_true(monkeypatch):
    # When arq dedups (enqueue_job returns None), enrichment IS already
    # scheduled/recent — we must still return True so the caller does NOT fall
    # back to the expensive inline enrichment. This is the debounce contract.
    fake = _FakePool(coalesce=True)

    async def _fake_create_pool(*a, **k):
        return fake

    monkeypatch.setattr(s, "create_pool", _fake_create_pool)
    ok = await s.enqueue_graph_enrichment(_UID)
    assert ok is True
    assert len(fake.calls) == 1


async def test_returns_false_when_pool_unreachable(monkeypatch):
    async def _boom_create_pool(*a, **k):
        raise RuntimeError("no redis")

    monkeypatch.setattr(s, "create_pool", _boom_create_pool)
    ok = await s.enqueue_graph_enrichment(_UID)
    # False => caller runs enrich_user_graph inline (never silently stops).
    assert ok is False


async def test_returns_false_when_enqueue_raises(monkeypatch):
    fake = _FakePool(boom=True)

    async def _fake_create_pool(*a, **k):
        return fake

    monkeypatch.setattr(s, "create_pool", _fake_create_pool)
    ok = await s.enqueue_graph_enrichment(_UID)
    assert ok is False


async def test_pool_is_cached_across_calls(monkeypatch):
    fake = _FakePool()
    created = {"n": 0}

    async def _counting_create_pool(*a, **k):
        created["n"] += 1
        return fake

    monkeypatch.setattr(s, "create_pool", _counting_create_pool)
    await s.enqueue_graph_enrichment(_UID)
    await s.enqueue_graph_enrichment(_UID)
    # A busy chat must not reconnect every turn.
    assert created["n"] == 1
    assert len(fake.calls) == 2
