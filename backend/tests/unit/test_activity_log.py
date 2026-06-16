"""Unit tests for the serialization activity_log uses (jsonify + compact JSON)."""
from __future__ import annotations

import json
from datetime import date, datetime
from uuid import uuid4

from src.shared.serialization import jsonify


class TestJsonify:
    def test_datetime(self):
        dt = datetime(2024, 1, 1, 12, 0)
        assert jsonify(dt) == "2024-01-01T12:00:00"

    def test_date(self):
        d = date(2024, 1, 1)
        assert jsonify(d) == "2024-01-01"

    def test_uuid(self):
        u = uuid4()
        assert jsonify(u) == str(u)

    def test_dict(self):
        u = uuid4()
        assert jsonify({"a": u}) == {"a": str(u)}

    def test_primitive(self):
        assert jsonify(42) == 42


class TestCompactJson:
    """activity_log persists payloads as json.dumps(..., separators=(',', ':'))."""

    def test_encodes_dict(self):
        assert json.dumps({"a": 1}, default=str, separators=(",", ":")) == '{"a":1}'

    def test_encodes_with_uuid(self):
        u = uuid4()
        result = json.dumps(jsonify({"id": u}), default=str, separators=(",", ":"))
        assert str(u) in result
