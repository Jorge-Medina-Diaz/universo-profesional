"""Unit tests for graph retrieval helpers (pure, no DB)."""
from __future__ import annotations

from types import SimpleNamespace
from uuid import uuid4

from src.graph.application.retrieval._helpers import (
    _attach_ranks,
    _coerce_uuid,
    _strip_quotes,
)


class TestStripQuotes:
    def test_none(self):
        assert _strip_quotes(None) == ""

    def test_string(self):
        assert _strip_quotes("hello") == "hello"

    def test_quoted(self):
        assert _strip_quotes('"abc"') == "abc"

    def test_number(self):
        assert _strip_quotes(42) == "42"


class TestCoerceUuid:
    def test_none(self):
        assert _coerce_uuid(None) is None

    def test_valid_str(self):
        u = uuid4()
        assert _coerce_uuid(str(u)) == u

    def test_quoted_str(self):
        u = uuid4()
        assert _coerce_uuid(f'"{u}"') == u

    def test_invalid(self):
        assert _coerce_uuid("not-a-uuid") is None


class TestAttachRanks:
    def test_empty(self):
        assert _attach_ranks([], lane="test") == []

    def test_ranks(self):
        items = [SimpleNamespace(score=1.0), SimpleNamespace(score=0.5)]
        result = _attach_ranks(items, lane="bm25")
        assert result[0].rank == 1
        assert result[0].lane == "bm25"
        assert result[1].rank == 2
