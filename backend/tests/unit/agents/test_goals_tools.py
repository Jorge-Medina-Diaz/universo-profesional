"""Unit tests for goals_tools pure helpers (no DB)."""
from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import uuid4

from src.agents.tools.goals_tools import VALID_HORIZONS, VALID_STATUS, _serialize


class TestSerialize:
    def test_full(self):
        g = SimpleNamespace(
            id=uuid4(),
            horizon="1_year",
            title="Learn Rust",
            description="Deep dive",
            status="active",
            target_date=datetime(2025, 1, 1, tzinfo=UTC),
            details={"subtasks": [{"title": "Read book", "done": False}]},
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
            completed_at=None,
        )
        d = _serialize(g)
        assert d["title"] == "Learn Rust"
        assert d["target_date"] == "2025-01-01T00:00:00+00:00"
        assert d["completed_at"] is None

    def test_no_target_date(self):
        g = SimpleNamespace(
            id=uuid4(),
            horizon="long_term",
            title="Goal",
            description=None,
            status="active",
            target_date=None,
            details=None,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
            completed_at=None,
        )
        d = _serialize(g)
        assert d["target_date"] is None
        assert d["details"] == {}


class TestConstants:
    def test_horizons(self):
        assert "3_months" in VALID_HORIZONS
        assert "long_term" in VALID_HORIZONS

    def test_status(self):
        assert "active" in VALID_STATUS
        assert "completed" in VALID_STATUS
