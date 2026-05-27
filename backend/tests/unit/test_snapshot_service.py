"""Unit tests for snapshot_service pure helpers."""
from __future__ import annotations

from datetime import date, datetime
from types import SimpleNamespace
from uuid import uuid4

from src.universe.application.snapshot_service import _as_dict, _coerce, _filter_internal


class TestCoerce:
    def test_datetime(self):
        dt = datetime(2024, 1, 1, 12, 0)
        assert _coerce(dt) == "2024-01-01T12:00:00"

    def test_date(self):
        d = date(2024, 1, 1)
        assert _coerce(d) == "2024-01-01"

    def test_uuid(self):
        u = uuid4()
        assert _coerce(u) == str(u)

    def test_list(self):
        u = uuid4()
        assert _coerce([1, u]) == [1, str(u)]

    def test_dict(self):
        u = uuid4()
        assert _coerce({"a": u}) == {"a": str(u)}

    def test_primitive(self):
        assert _coerce(42) == 42
        assert _coerce("hello") == "hello"


class TestFilterInternal:
    def test_drops_internal_columns(self):
        row = {"id": 1, "user_id": 2, "embedding": "x", "deleted_at": None, "updated_at": "t", "name": "ok"}
        out = _filter_internal(row)
        assert out == {"id": 1, "name": "ok"}


class TestAsDict:
    def test_with_table(self):
        obj = SimpleNamespace()
        obj.__table__ = SimpleNamespace(columns=[SimpleNamespace(name="a"), SimpleNamespace(name="b")])
        obj.a = 1
        obj.b = uuid4()
        result = _as_dict(obj)
        assert result["a"] == 1
        assert result["b"] == str(obj.b)

    def test_without_table(self):
        obj = {"x": 1}
        assert _as_dict(obj) == {"x": 1}
