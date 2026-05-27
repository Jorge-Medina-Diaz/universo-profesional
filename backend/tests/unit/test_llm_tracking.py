"""Unit tests for LLM tracking domain."""
from __future__ import annotations

from uuid import uuid4

from src.llm_tracking.domain.entities import LlmUsageLog, _int


class TestInt:
    def test_int_with_valid(self):
        assert _int(5) == 5
        assert _int("3") == 3

    def test_int_with_none(self):
        assert _int(None) == 0

    def test_int_with_invalid(self):
        assert _int("bad") == 0


class TestLlmUsageLog:
    def test_from_agno_metrics(self):
        log = LlmUsageLog.from_agno_metrics(
            user_id=uuid4(),
            provider="anthropic",
            model="claude",
            metrics={
                "input_tokens": 10,
                "output_tokens": 5,
                "cache_read_tokens": 2,
                "cache_write_tokens": 1,
                "total_tokens": 16,
                "duration": 1.5,
            },
        )
        assert log.input_tokens == 10
        assert log.output_tokens == 5
        assert log.duration_ms == 1500
        assert log.cost_eur is None

    def test_from_agno_metrics_no_duration(self):
        log = LlmUsageLog.from_agno_metrics(
            user_id=uuid4(),
            provider="anthropic",
            model="claude",
            metrics={},
        )
        assert log.duration_ms is None
