"""Shared LLM client interface + Anthropic/OpenAI/Mock implementations.

Used by:
  - documents/ai_generation: CV/cover-letter generation
  - integrations/pdf_cv_parser: structured extraction from CV PDFs
  - universe/suggestions: LLM-driven suggestion provider

The interface is intentionally narrow:
  - `complete_text(...)` — free text completion (used for prose suggestions)
  - `structured(...)` — JSON output matching a Pydantic schema (used for PDF
    extraction and CV generation pipelines)

Real providers are only imported when `LLM_PROVIDER != "mock"` to keep
production dependencies light in mock mode and to avoid SDK incompatibilities
in CI.
"""
from __future__ import annotations

import json
from typing import Any, Protocol, TypeVar

import structlog
from pydantic import BaseModel

from src.shared.config import get_settings

logger = structlog.get_logger(__name__)

T = TypeVar("T", bound=BaseModel)


class LlmClient(Protocol):
    async def complete_text(
        self,
        *,
        system: str,
        prompt: str,
        max_tokens: int = 1024,
        temperature: float = 0.4,
    ) -> str: ...

    async def structured(
        self,
        *,
        system: str,
        prompt: str,
        schema: type[T],
        max_tokens: int = 4096,
        temperature: float = 0.0,
    ) -> T: ...


# --- Mock ------------------------------------------------------------------


class MockLlmClient:
    """Deterministic mock useful for tests and offline development."""

    last_usage: dict[str, int] | None = None

    async def complete_text(
        self, *, system: str, prompt: str, max_tokens: int = 1024, temperature: float = 0.4
    ) -> str:
        self.last_usage = None
        return (
            "[mock-llm] " + prompt[:200] + ("…" if len(prompt) > 200 else "")
        )

    async def structured(
        self,
        *,
        system: str,
        prompt: str,
        schema: type[T],
        max_tokens: int = 4096,
        temperature: float = 0.0,
    ) -> T:
        self.last_usage = None
        # Build the laziest possible instance — useful only to verify wiring
        return schema.model_construct()


# --- Anthropic -------------------------------------------------------------


class AnthropicLlmClient:
    def __init__(self) -> None:
        from anthropic import AsyncAnthropic

        self._client = AsyncAnthropic()
        self._model = "claude-sonnet-4-6"
        self.last_usage: dict[str, int] | None = None

    def _extract_usage(self, resp: Any) -> dict[str, int]:
        usage = getattr(resp, "usage", None) or {}
        return {
            "input_tokens": int(getattr(usage, "input_tokens", 0) or 0),
            "output_tokens": int(getattr(usage, "output_tokens", 0) or 0),
            "cache_read_tokens": int(getattr(usage, "cache_read_input_tokens", 0) or 0),
            "cache_write_tokens": int(getattr(usage, "cache_creation_input_tokens", 0) or 0),
            "total_tokens": int(getattr(usage, "input_tokens", 0) or 0)
            + int(getattr(usage, "output_tokens", 0) or 0),
        }

    async def complete_text(
        self, *, system: str, prompt: str, max_tokens: int = 1024, temperature: float = 0.4
    ) -> str:
        resp = await self._client.messages.create(
            model=self._model,
            max_tokens=max_tokens,
            temperature=temperature,
            system=system,
            messages=[{"role": "user", "content": prompt}],
        )
        self.last_usage = self._extract_usage(resp)
        return "".join(b.text for b in resp.content if getattr(b, "type", "") == "text")

    async def structured(
        self,
        *,
        system: str,
        prompt: str,
        schema: type[T],
        max_tokens: int = 4096,
        temperature: float = 0.0,
    ) -> T:
        tool_schema = {
            "name": "emit_structured",
            "description": f"Return the {schema.__name__} as JSON.",
            "input_schema": schema.model_json_schema(),
        }
        resp = await self._client.messages.create(
            model=self._model,
            max_tokens=max_tokens,
            temperature=temperature,
            system=system,
            tools=[tool_schema],
            tool_choice={"type": "tool", "name": "emit_structured"},
            messages=[{"role": "user", "content": prompt}],
        )
        self.last_usage = self._extract_usage(resp)
        for block in resp.content:
            if getattr(block, "type", "") == "tool_use" and block.name == "emit_structured":
                return schema.model_validate(block.input)
        raise RuntimeError("Anthropic did not return tool_use block")


# --- OpenAI ----------------------------------------------------------------


class OpenAiLlmClient:
    def __init__(self) -> None:
        from openai import AsyncOpenAI

        self._client = AsyncOpenAI()
        self._model = "gpt-4o-mini"
        self.last_usage: dict[str, int] | None = None

    def _extract_usage(self, resp: Any) -> dict[str, int]:
        usage = getattr(resp, "usage", None) or {}
        return {
            "input_tokens": int(getattr(usage, "prompt_tokens", 0) or 0),
            "output_tokens": int(getattr(usage, "completion_tokens", 0) or 0),
            "cache_read_tokens": int(getattr(usage, "prompt_tokens_details", {}).get("cached_tokens", 0) or 0),
            "cache_write_tokens": 0,
            "total_tokens": int(getattr(usage, "total_tokens", 0) or 0),
        }

    async def complete_text(
        self, *, system: str, prompt: str, max_tokens: int = 1024, temperature: float = 0.4
    ) -> str:
        resp = await self._client.chat.completions.create(
            model=self._model,
            max_tokens=max_tokens,
            temperature=temperature,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": prompt},
            ],
        )
        self.last_usage = self._extract_usage(resp)
        return resp.choices[0].message.content or ""

    async def structured(
        self,
        *,
        system: str,
        prompt: str,
        schema: type[T],
        max_tokens: int = 4096,
        temperature: float = 0.0,
    ) -> T:
        resp = await self._client.chat.completions.create(
            model=self._model,
            max_tokens=max_tokens,
            temperature=temperature,
            response_format={
                "type": "json_schema",
                "json_schema": {
                    "name": schema.__name__,
                    "schema": schema.model_json_schema(),
                    "strict": True,
                },
            },
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": prompt},
            ],
        )
        self.last_usage = self._extract_usage(resp)
        content = resp.choices[0].message.content or "{}"
        return schema.model_validate(json.loads(content))


# --- Factory ---------------------------------------------------------------


_client: LlmClient | None = None


def get_llm_client() -> LlmClient:
    global _client
    if _client is not None:
        return _client
    settings = get_settings()
    provider = settings.llm_provider_resolved
    if provider == "anthropic":
        try:
            _client = AnthropicLlmClient()
        except Exception as exc:
            logger.warning("anthropic_init_failed_falling_back_to_mock", error=str(exc))
            settings.assert_llm_usable()
            _client = MockLlmClient()
    elif provider == "openai":
        try:
            _client = OpenAiLlmClient()
        except Exception as exc:
            logger.warning("openai_init_failed_falling_back_to_mock", error=str(exc))
            settings.assert_llm_usable()
            _client = MockLlmClient()
    else:
        # No real provider resolved — refuse the fabricating mock where it
        # isn't allowed (prod without a key) instead of silently using it.
        settings.assert_llm_usable()
        _client = MockLlmClient()
    return _client


def reset_llm_client() -> None:
    """Test-only."""
    global _client
    _client = None
