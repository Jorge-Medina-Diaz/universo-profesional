"""Deterministic scripted LLM for offline agent-loop tests (R5).

The default "mock" provider is an OpenAI-compatible client pointed at an
unreachable URL — it lets the app boot offline but any actual model call fails
loudly (by design: we must never serve fabricated content as real). That makes
the agent LOOP itself (routing → tool call → tool exec → final text → HITL
pause) untestable without a real LLM + network + spend.

`FakeScriptedModel` closes that gap: it is a real agno `Model` whose responses
are a fixed script, so a test can drive the exact tool-call / text sequence it
wants, deterministically and offline. It is OPT-IN — never the default — via
`scripted_model(...)` (a context manager that `_build_model` consults), so it
can't accidentally back a real user's agent.

Each scripted step is a dict:
  * text  : {"content": "..."}                      → assistant text (ends loop)
  * tool  : {"tool": "name", "args": {...},
             "content": "optional preamble"}          → one tool call

The model pops one step per invocation; once exhausted it returns a terminal
text so the loop always terminates (a runaway script can't hang the test).
"""
from __future__ import annotations

import json
from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from typing import Any

from agno.models.base import Model
from agno.models.response import ModelResponse

# Opt-in override, mirroring factory._byok_override: when set, _build_model
# returns a FakeScriptedModel wired to these steps instead of a real/mock model.
_scripted_steps: ContextVar[list[dict[str, Any]] | None] = ContextVar(
    "_scripted_steps", default=None
)


class FakeScriptedModel(Model):
    """An agno Model that replays a fixed script of text/tool-call steps."""

    def __init__(self, steps: list[dict[str, Any]] | None = None) -> None:
        super().__init__(id="fake-scripted", provider="fake")
        self._steps: list[dict[str, Any]] = list(steps or [])
        self._i = 0

    def _next(self) -> dict[str, Any]:
        if self._i >= len(self._steps):
            # Terminal text so the agent loop always ends, even if the script
            # under-specifies the turn count.
            return {"content": ""}
        step = self._steps[self._i]
        self._i += 1
        return step

    def _to_response(self, step: dict[str, Any]) -> ModelResponse:
        if step.get("tool"):
            return ModelResponse(
                role="assistant",
                content=step.get("content", ""),
                tool_calls=[
                    {
                        "id": f"call_{self._i}",
                        "type": "function",
                        "function": {
                            "name": step["tool"],
                            "arguments": json.dumps(step.get("args", {})),
                        },
                    }
                ],
            )
        return ModelResponse(role="assistant", content=step.get("content", ""))

    # --- agno Model contract (the 6 abstract methods) --------------------------
    async def ainvoke(self, *args: Any, **kwargs: Any) -> ModelResponse:
        return self._to_response(self._next())

    def invoke(self, *args: Any, **kwargs: Any) -> ModelResponse:
        return self._to_response(self._next())

    async def ainvoke_stream(self, *args: Any, **kwargs: Any):  # type: ignore[no-untyped-def]
        yield self._to_response(self._next())

    def invoke_stream(self, *args: Any, **kwargs: Any) -> Iterator[ModelResponse]:
        yield self._to_response(self._next())

    def _parse_provider_response(self, response: Any, **kwargs: Any) -> ModelResponse:
        # ainvoke/invoke already produce a ModelResponse — pass it through.
        return response

    def _parse_provider_response_delta(self, response: Any) -> ModelResponse:
        return response


def get_scripted_steps() -> list[dict[str, Any]] | None:
    """Return the active scripted steps, or None (no override)."""
    return _scripted_steps.get()


@contextmanager
def scripted_model(steps: list[dict[str, Any]]):
    """Within this block, `_build_model` returns a FakeScriptedModel(steps).

    Use in tests to drive a deterministic agent loop offline. Opt-in only.

    CAVEAT for team-level tests: `get_universe_team()` is `@lru_cache`d, so a
    team built once (with a real/mock model) is reused and will NOT pick up this
    override. To script a whole team, build it inside this block via the
    uncached `_build_universe_team()` (or clear the cache first). A single Agent
    built directly with `FakeScriptedModel(...)` — the simplest case — is
    unaffected.
    """
    token = _scripted_steps.set(list(steps))
    try:
        yield
    finally:
        _scripted_steps.reset(token)
