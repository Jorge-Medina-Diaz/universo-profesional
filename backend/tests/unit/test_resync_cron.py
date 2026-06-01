"""R10: resync_cron fans out GitHub re-syncs, no real external calls.

with_user_session is mocked so the test asserts the fan-out logic (enqueue per
connection, per-uid resilience, redis-None handling) without a DB or GitHub API.
"""
from __future__ import annotations

import contextlib

from src.integrations.infrastructure import tasks as t


class _FakeResult:
    def __init__(self, rows):
        self._rows = rows

    def all(self):
        return [(r,) for r in self._rows]


class _FakeSession:
    def __init__(self, rows):
        self._rows = rows

    async def execute(self, *a, **k):
        return _FakeResult(self._rows)


def _fake_session_factory(rows):
    @contextlib.asynccontextmanager
    async def _cm(_user_id):
        yield _FakeSession(rows)

    return _cm


class _FakeRedis:
    def __init__(self, boom=False):
        self.calls = []
        self._boom = boom

    async def enqueue_job(self, name, **kw):
        if self._boom:
            raise RuntimeError("enqueue down")
        self.calls.append((name, kw))


async def test_enqueues_one_job_per_due_github_connection(monkeypatch):
    uids = [
        "11111111-1111-1111-1111-111111111111",
        "22222222-2222-2222-2222-222222222222",
    ]
    monkeypatch.setattr("src.shared.db.with_user_session", _fake_session_factory(uids))
    fake = _FakeRedis()
    res = await t.resync_cron({"redis": fake})
    assert res["enqueued"] == 2 and res["mode"] == "arq"
    assert all(c[0] == "run_github_sync_task" for c in fake.calls)
    assert {c[1]["user_id"] for c in fake.calls} == set(uids)


async def test_noop_when_no_due_connections(monkeypatch):
    monkeypatch.setattr("src.shared.db.with_user_session", _fake_session_factory([]))
    res = await t.resync_cron({"redis": _FakeRedis()})
    assert res == {"connections": 0, "enqueued": 0, "mode": "noop"}


async def test_per_uid_enqueue_error_does_not_abort_batch(monkeypatch):
    monkeypatch.setattr("src.shared.db.with_user_session", _fake_session_factory(["a", "b"]))
    res = await t.resync_cron({"redis": _FakeRedis(boom=True)})
    # Loop survived both failures; nothing enqueued, but it didn't raise.
    assert res["connections"] == 2 and res["enqueued"] == 0
