"""Shared specialist builder.

Every specialist follows the same shape: focused instructions, a pair of
tools (propose UI + persist), one model. Centralizing the constructor keeps
the per-entity files to ~15 lines of pure intent.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class SpecialistSpec:
    """Immutable descriptor for an entity-CRUD specialist.

    Moving the unique per-specialist configuration (instructions, role, tools)
    into a dataclass lets each specialist file shrink to a one-liner that
    delegates to :func:`build_specialist_from_spec`.
    """

    name: str
    role: str
    instructions: list[str]
    propose_tool: Any
    upsert_tool: Any
    extra_tools: list[Any] = field(default_factory=list)


def build_specialist_from_spec(spec: SpecialistSpec, *, db: Any):  # type: ignore[no-untyped-def]
    """Build a specialist from a :class:`SpecialistSpec` descriptor.

    Automatically wires the common CRUD toolkit:
    ``propose_tool``, ``upsert_tool``, ``find_existing``,
    ``get_profile_completeness``, ``present_questionnaire``.
    Any additional tools (e.g. ``mark_stale``, ``propose_artifact``) are
    appended via ``extra_tools``.
    """
    from src.agents.tools.coherence_tools import find_existing  # noqa: PLC0415
    from src.agents.tools.discovery_tools import get_profile_completeness  # noqa: PLC0415
    from src.agents.tools.ui_widgets import present_questionnaire  # noqa: PLC0415

    tools = [
        spec.propose_tool,
        spec.upsert_tool,
        find_existing,
        get_profile_completeness,
        present_questionnaire,
    ]
    tools.extend(spec.extra_tools)

    return build_specialist(
        name=spec.name,
        role=spec.role,
        db=db,
        tools=tools,
        instructions=spec.instructions,
    )


def build_specialist(
    *,
    name: str,
    role: str,
    instructions: list[str],
    tools: list[Any],
    db: Any,
    tier: str = "specialist",
    tool_call_limit: int = 8,
):
    """Build one focused specialist agent.

    `tier` defaults to "specialist" (cheap/fast model) — that is the whole
    point of the coordinator + specialists split. A reasoning-heavy
    specialist can pass `tier="coordinator"` to opt back into the strong
    model if quality regresses. `tool_call_limit` bounds runaway tool loops.
    """
    from agno.agent import Agent  # noqa: PLC0415

    from src.agents.factory import _build_model  # noqa: PLC0415

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
