"""Unit tests for shared metrics."""
from __future__ import annotations

from types import SimpleNamespace

from src.shared.metrics import record_agent_tokens


class TestRecordAgentTokens:
    def test_none_metrics(self):
        out = record_agent_tokens("test", None)
        assert out == {}

    def test_partial_metrics(self):
        metrics = SimpleNamespace(input_tokens=10, output_tokens=5)
        out = record_agent_tokens("test", metrics)
        assert out["input_tokens"] == 10
        assert out["output_tokens"] == 5
        assert out["total_tokens"] == 0

    def test_invalid_values(self):
        metrics = SimpleNamespace(input_tokens="bad", output_tokens=None)
        out = record_agent_tokens("test", metrics)
        assert out["input_tokens"] == 0
        assert out["output_tokens"] == 0
