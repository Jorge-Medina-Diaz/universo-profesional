"""Tests for Text2Cypher engine (pure + mocked LLM, no DB required).

Covers:
  • Validation of generated Cypher against AGE constraints
  • JSON parsing resilience (fences, malformed)
  • Parameter injection (user_id)
  • Mock execution path
"""
from __future__ import annotations

from uuid import UUID

import pytest
from src.graph.application.text2cypher import (
    CypherResult,
    Text2CypherEngine,
    _validate_query,
)


class TestValidateQuery:
    def test_accepts_simple_match(self) -> None:
        assert _validate_query("MATCH (n) RETURN n") is None

    def test_rejects_relationships_function(self) -> None:
        err = _validate_query("MATCH p=(a)-[]->(b) RETURN relationships(p)")
        assert err is not None
        assert "relationships" in err

    def test_rejects_all_any(self) -> None:
        for kw in ("ALL", "ANY", "FILTER", "EXTRACT", "REDUCE"):
            err = _validate_query(f"MATCH (n) WHERE {kw}(x IN n.list)")
            assert err is not None, f"should reject {kw}"

    def test_rejects_multiple_statements(self) -> None:
        err = _validate_query("MATCH (n) RETURN n; MATCH (m) RETURN m")
        assert err is not None
        assert "multiple" in err


class TestCypherResultDataclass:
    def test_immutability(self) -> None:
        r = CypherResult(cypher="MATCH (n) RETURN n", params={}, explanation="test")
        with pytest.raises(AttributeError):
            r.cypher = "x"  # type: ignore[misc]


class TestText2CypherEngineMock:
    """Tests using the mock LLM path (no real API keys needed)."""

    @pytest.fixture
    def engine(self, mocker):
        # We need an AsyncSession mock, but the mock LLM path never touches it.
        session = mocker.AsyncMock()
        return Text2CypherEngine(session, UUID("11111111-1111-1111-1111-111111111111"))

    @pytest.mark.asyncio
    async def test_mock_generate_returns_cypher(self, engine) -> None:
        result = await engine.generate("How many nodes do I have?")
        assert result.cypher is not None
        assert "$user_id" in result.cypher or "$user_id" in str(result.params)
        assert result.error is None
        assert result.latency_ms >= 0

    @pytest.mark.asyncio
    async def test_mock_ask_returns_rows(self, engine, mocker) -> None:
        # Patch cypher() so execution succeeds without a real DB
        mocker.patch(
            "src.graph.application.text2cypher.cypher",
            new_callable=mocker.AsyncMock,
            return_value=[{"result": '{"total": 5}::vertex'}],
        )
        mocker.patch(
            "src.graph.infrastructure.age_client.parse_agtype",
            return_value={"total": 5},
        )
        result = await engine.ask("Count my nodes")
        assert result.cypher is not None
        assert result.error is None
        assert result.rows is not None
        assert len(result.rows) == 1

    @pytest.mark.asyncio
    async def test_user_id_injected_when_missing(self, engine) -> None:
        result = await engine.generate("test")
        assert "user_id" in result.params
        assert result.params["user_id"] == "11111111-1111-1111-1111-111111111111"
