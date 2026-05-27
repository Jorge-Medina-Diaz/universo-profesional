"""Unit tests for text2cypher validation."""
from __future__ import annotations

from src.graph.application.text2cypher import _validate_query


class TestValidateQuery:
    def test_empty(self):
        assert _validate_query("") == "empty query"

    def test_forbidden_function(self):
        assert _validate_query("MATCH (n) RETURN relationships(n)") is not None

    def test_multiple_statements(self):
        assert _validate_query("MATCH (n) RETURN n; MATCH (m) RETURN m") is not None

    def test_valid(self):
        assert _validate_query("MATCH (n) RETURN count(n)") is None
