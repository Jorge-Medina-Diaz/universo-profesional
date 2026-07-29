"""Unit tests for goals_router helpers."""
from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import uuid4

from src.universe.interfaces.api.goals_router import VALID_HORIZONS, VALID_STATUS, _serialize


class TestSerialize:
    def test_serializes_all_fields(self):
        now = datetime.now(UTC)
        g = SimpleNamespace(
            id=uuid4(),
            horizon="1_year",
            title="Learn Rust",
            description="Deep dive",
            status="active",
            target_date=None,
            details={"subtasks": []},
            created_at=now,
            updated_at=now,
            completed_at=None,
        )
        out = _serialize(g)
        assert out["id"] == str(g.id)
        assert out["horizon"] == "1_year"
        assert out["title"] == "Learn Rust"
        assert out["target_date"] is None
        assert out["completed_at"] is None

    def test_with_target_date(self):
        now = datetime.now(UTC)
        g = SimpleNamespace(
            id=uuid4(),
            horizon="3_months",
            title="T",
            description=None,
            status="active",
            target_date=now.date(),
            details=None,
            created_at=now,
            updated_at=now,
            completed_at=None,
        )
        out = _serialize(g)
        assert out["target_date"] == now.date().isoformat()


class TestValidConstants:
    def test_horizons(self):
        assert "3_months" in VALID_HORIZONS
        assert "long_term" in VALID_HORIZONS

    def test_status(self):
        assert "active" in VALID_STATUS
        assert "completed" in VALID_STATUS
