"""Unit tests for shared.serialization."""
from __future__ import annotations

from datetime import date, datetime
from uuid import UUID, uuid4

from pydantic import BaseModel

from src.shared.serialization import jsonify


class DummyModel(BaseModel):
    name: str
    count: int


class TestJsonify:
    def test_passthrough_primitive(self):
        assert jsonify(42) == 42
        assert jsonify("hello") == "hello"
        assert jsonify(None) is None

    def test_basemodel(self):
        m = DummyModel(name="x", count=5)
        assert jsonify(m) == {"name": "x", "count": 5}

    def test_datetime(self):
        dt = datetime(2024, 1, 15, 10, 30, 0)
        assert jsonify(dt) == "2024-01-15T10:30:00"

    def test_date(self):
        d = date(2024, 1, 15)
        assert jsonify(d) == "2024-01-15"

    def test_uuid(self):
        u = uuid4()
        assert jsonify(u) == str(u)

    def test_dict(self):
        assert jsonify({"a": 1, "b": DummyModel(name="x", count=2)}) == {
            "a": 1,
            "b": {"name": "x", "count": 2},
        }

    def test_list(self):
        u = uuid4()
        assert jsonify([1, datetime(2024, 1, 1), u]) == [1, "2024-01-01T00:00:00", str(u)]

    def test_nested(self):
        u = uuid4()
        result = jsonify({"items": [{"id": u, "created": date(2024, 1, 1)}]})
        assert result["items"][0]["id"] == str(u)
        assert result["items"][0]["created"] == "2024-01-01"
