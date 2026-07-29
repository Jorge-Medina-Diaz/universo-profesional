"""Unit tests for LLM client mock and helpers."""
from __future__ import annotations

from types import SimpleNamespace

from src.shared.llm_client import (
    AnthropicLlmClient,
    MockLlmClient,
    OpenAiLlmClient,
    get_llm_client,
    reset_llm_client,
)


class TestMockLlmClient:
    async def test_complete_text(self):
        client = MockLlmClient()
        result = await client.complete_text(system="s", prompt="hello world")
        assert result.startswith("[mock-llm]")

    async def test_structured(self):
        class DummySchema:
            @classmethod
            def model_construct(cls):
                return cls()

        client = MockLlmClient()
        result = await client.structured(system="s", prompt="p", schema=DummySchema)
        assert isinstance(result, DummySchema)


class TestExtractUsage:
    def test_anthropic_extract_usage(self):
        client = AnthropicLlmClient.__new__(AnthropicLlmClient)
        usage = SimpleNamespace(input_tokens=10, output_tokens=5, cache_read_input_tokens=2, cache_creation_input_tokens=1)
        resp = SimpleNamespace(usage=usage)
        out = client._extract_usage(resp)
        assert out["input_tokens"] == 10
        assert out["output_tokens"] == 5
        assert out["cache_read_tokens"] == 2
        assert out["cache_write_tokens"] == 1
        assert out["total_tokens"] == 15

    def test_openai_extract_usage(self):
        client = OpenAiLlmClient.__new__(OpenAiLlmClient)
        usage = SimpleNamespace(prompt_tokens=10, completion_tokens=5, total_tokens=15, prompt_tokens_details={"cached_tokens": 2})
        resp = SimpleNamespace(usage=usage)
        out = client._extract_usage(resp)
        assert out["input_tokens"] == 10
        assert out["output_tokens"] == 5
        assert out["cache_read_tokens"] == 2
        assert out["cache_write_tokens"] == 0
        assert out["total_tokens"] == 15

    def test_extract_usage_no_usage(self):
        client = AnthropicLlmClient.__new__(AnthropicLlmClient)
        resp = SimpleNamespace(usage=None)
        out = client._extract_usage(resp)
        assert out["total_tokens"] == 0


class TestGetLlmClient:
    def test_returns_mock_by_default(self):
        reset_llm_client()
        client = get_llm_client()
        assert isinstance(client, MockLlmClient)
