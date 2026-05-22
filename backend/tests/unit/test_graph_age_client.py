"""Smoke tests for the AGE client helpers (pure, no DB).

Protects the Sprint-cleanup critical fix: `column_defs` interpolation in
`cypher()` is the one spot where an identifier reaches the SQL string, so
it must reject anything that isn't a `<ident> agtype` list.
"""
from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

import pytest

from src.graph.infrastructure.age_client import (
    _serialize_params,
    _validate_column_defs,
    _validate_graph_name,
    parse_agtype,
)


class TestColumnDefsValidation:
    def test_accepts_single_column(self) -> None:
        _validate_column_defs("result agtype")  # no raise

    def test_accepts_multi_column(self) -> None:
        _validate_column_defs("a agtype, b agtype, c agtype")  # no raise

    @pytest.mark.parametrize(
        "bad",
        [
            "x agtype); DROP TABLE users; --",
            "result text",  # wrong type
            "result",  # missing type
            "1col agtype",  # identifier can't start with digit
            "",  # empty
            "result agtype; SELECT 1",
        ],
    )
    def test_rejects_injection_and_malformed(self, bad: str) -> None:
        with pytest.raises(ValueError):
            _validate_column_defs(bad)


class TestGraphNameValidation:
    def test_accepts_valid(self) -> None:
        _validate_graph_name("universe_personal")

    @pytest.mark.parametrize("bad", ["bad-name", "drop;table", "1graph", ""])
    def test_rejects_invalid(self, bad: str) -> None:
        with pytest.raises(ValueError):
            _validate_graph_name(bad)


class TestParseAgtype:
    @pytest.mark.parametrize(
        ("raw", "expected"),
        [
            ('{"a": 1}::vertex', {"a": 1}),
            ('{"x": "y"}::edge', {"x": "y"}),
            ("42::numeric", 42),
            ('"plain string"', "plain string"),
            ("123", 123),
            (None, None),
        ],
    )
    def test_strips_suffixes(self, raw, expected) -> None:
        assert parse_agtype(raw) == expected


class TestSerializeParams:
    def test_empty(self) -> None:
        assert _serialize_params(None) == "{}"
        assert _serialize_params({}) == "{}"

    def test_uuid_becomes_string(self) -> None:
        uid = UUID("11111111-1111-1111-1111-111111111111")
        out = _serialize_params({"id": uid})
        assert str(uid) in out

    def test_list_and_scalars(self) -> None:
        out = _serialize_params({"nums": [1, 2, 3], "name": "x", "flag": True})
        assert '"nums"' in out and '"name"' in out

    def test_datetime_falls_back_to_str(self) -> None:
        # default=str keeps the call from blowing up on datetimes.
        out = _serialize_params({"ts": datetime(2026, 1, 1, tzinfo=UTC)})
        assert "2026-01-01" in out
