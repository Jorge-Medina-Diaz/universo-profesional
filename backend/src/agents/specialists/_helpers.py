"""Shared specialist builder.

Every specialist follows the same shape: focused instructions, a pair of
tools (propose UI + persist), one model. Centralizing the constructor keeps
the per-entity files to ~15 lines of pure intent.
"""
from __future__ import annotations

from typing import Any


def build_specialist(
    *,
    name: str,
    role: str,
    instructions: list[str],
    tools: list[Any],
    db: Any,
    tier: str = "specialist",
    tool_call_limit: int = 8,
):  # type: ignore[no-untyped-def]
    """Build one focused specialist agent.

    `tier` defaults to "specialist" (cheap/fast model) — that is the whole
    point of the coordinator + specialists split. A reasoning-heavy
    specialist can pass `tier="coordinator"` to opt back into the strong
    model if quality regresses. `tool_call_limit` bounds runaway tool loops.
    """
    from agno.agent import Agent

    from src.agents.factory import _build_model

    return Agent(
        name=name,
        role=role,
        model=_build_model(tier),  # type: ignore[arg-type]
        db=db,
        tools=tools,
        instructions=instructions,
        add_history_to_context=True,
        update_memory_on_run=True,
        markdown=False,
        tool_call_limit=tool_call_limit,
    )
