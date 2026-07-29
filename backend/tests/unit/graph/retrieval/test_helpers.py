"""Unit tests for retrieval helpers (pure, no DB)."""
from __future__ import annotations

from uuid import uuid4

from src.graph.application.retrieval._base import ScoredItem
from src.graph.application.retrieval._helpers import (
    _attach_ranks,
    _coerce_uuid,
    _strip_quotes,
)


class TestAttachRanks:
    def test_ranks_start_at_one(self):
        items = [
            ScoredItem(entity_id=uuid4(), kind="skill", name="A", score=1.0),
            ScoredItem(entity_id=uuid4(), kind="skill", name="B", score=0.5),
        ]
        out = _attach_ranks(items, lane="bm25")
        assert out[0].rank == 1
        assert out[1].rank == 2
        assert out[0].lane == "bm25"


class TestStripQuotes:
    def test_none(self):
        assert _strip_quotes(None) == ""

    def test_strips_quotes(self):
        assert _strip_quotes('"hello"') == "hello"

    def test_no_quotes(self):
        assert _strip_quotes("hello") == "hello"


class TestCoerceUuid:
    def test_none(self):
        assert _coerce_uuid(None) is None

    def test_valid_uuid(self):
        u = uuid4()
        assert _coerce_uuid(str(u)) == u

    def test_valid_uuid_with_quotes(self):
        u = uuid4()
        assert _coerce_uuid(f'"{u}"') == u

    def test_invalid(self):
        assert _coerce_uuid("not-a-uuid") is None
