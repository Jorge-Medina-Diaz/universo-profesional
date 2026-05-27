"""Unit tests for activity_log pure helpers."""
from __future__ import annotations

from datetime import date, datetime
from uuid import uuid4

from src.shared.activity_log import _coerce, _json_encode


class TestActivityLogCoerce:
    def test_datetime(self):
        dt = datetime(2024, 1, 1, 12, 0)
        assert _coerce(dt) == "2024-01-01T12:00:00"

    def test_date(self):
        d = date(2024, 1, 1)
        assert _coerce(d) == "2024-01-01"

    def test_uuid(self):
        u = uuid4()
        assert _coerce(u) == str(u)

    def test_dict(self):
        u = uuid4()
        assert _coerce({"a": u}) == {"a": str(u)}

    def test_primitive(self):
        assert _coerce(42) == 42


class TestJsonEncode:
    def test_encodes_dict(self):
        assert _json_encode({"a": 1}) == '{"a":1}'

    def test_encodes_with_uuid(self):
        u = uuid4()
        result = _json_encode({"id": u})
        assert str(u) in result
