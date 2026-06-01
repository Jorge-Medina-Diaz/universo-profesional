"""R5: FakeScriptedModel drives the agno agent loop offline + deterministically.

Proves the loop works without a real LLM, network, or spend: a scripted tool
call is actually executed, its result is fed back, and the scripted final text
is returned. Also asserts the factory honors the opt-in scripted override so
larger flows can be driven the same way. DB-free (Agent db=None).
"""
from __future__ import annotations

from src.agents.infrastructure.fake_llm import (
    FakeScriptedModel,
    get_scripted_steps,
    scripted_model,
)


async def test_scripted_model_runs_tool_then_returns_text():
    from agno.agent import Agent
    from agno.tools import tool

    calls = {"echo": 0}

    @tool
    def echo(text: str) -> str:
        """Echo the text back."""
        calls["echo"] += 1
        return f"echoed:{text}"

    model = FakeScriptedModel(
        steps=[
            {"tool": "echo", "args": {"text": "hi"}},
            {"content": "Done."},
        ]
    )
    agent = Agent(name="t", model=model, tools=[echo], db=None, telemetry=False)
    out = await agent.arun("please echo hi", stream=False)

    assert calls["echo"] == 1  # the scripted tool actually executed
    assert getattr(out, "content", None) == "Done."


async def test_scripted_model_text_only_terminates():
    from agno.agent import Agent

    model = FakeScriptedModel(steps=[{"content": "hello world"}])
    agent = Agent(name="t", model=model, db=None, telemetry=False)
    out = await agent.arun("hi", stream=False)
    assert getattr(out, "content", None) == "hello world"


def test_factory_honors_scripted_override():
    import src.agents.factory as f

    assert get_scripted_steps() is None  # off by default
    with scripted_model([{"content": "x"}]):
        m = f._build_model("coordinator")
        assert isinstance(m, FakeScriptedModel)
    # contextvar resets on exit → real/mock model selection restored
    assert get_scripted_steps() is None
