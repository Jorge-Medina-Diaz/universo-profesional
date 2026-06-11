"""Shared specialist builder.

Every specialist follows the same shape: focused instructions, a pair of
tools (propose UI + persist), one model. Centralizing the constructor keeps
the per-entity files to ~15 lines of pure intent.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

# Shared natural-conversation doctrine. Prepended to EVERY specialist's
# instructions in `build_specialist` (the single choke point — both
# `build_specialist_from_spec` and the advisory/vertical specialists route
# through it), so the per-specialist files carry only their unique capture
# rubric, never a restatement of "how to converse". Kept short + static so it
# stays inside the cached system-prompt prefix.
#
# Root cause it fixes: the literal-minded specialist model used to march through
# each file's numbered "FLUJO DE DESCUBRIMIENTO 1..N" like a form, producing the
# repetitive/robotic feel. These four lines make discovery a palette, not a
# script, and tell the model to USE the already-injected context instead of
# re-asking. The "sin guiones" line is scoped to *questions* and explicitly
# exempts the verticals' mandatory tool sequences (search_rubrics →
# present_deep_dive → propose_* → present_widget), which must still run in order.
CONVERSATION_DOCTRINE: list[str] = [
    "CONVERSA, NO INTERROGUES: eres un compañero, no un formulario. Antes de preguntar, "
    "lee SIEMPRE el contexto ya inyectado (resumen del universo, digest de la conversación, "
    "historial reciente, preferencias). NUNCA re-preguntes algo que el usuario ya contó o "
    "que ya consta en su universo; si ya lo sabes, úsalo y avanza.",
    "SIN GUIONES DE PREGUNTAS: cuando descubras el perfil preguntando, las 'dimensiones' o "
    "ejemplos que listen tus instrucciones son un MENÚ de lo que podrías explorar, no un "
    "cuestionario a recorrer en orden. Cubre solo lo que falte y aporte, conectando con lo "
    "que el usuario acaba de decir. (Las secuencias de herramientas que tus instrucciones "
    "marquen como pasos obligatorios SÍ se ejecutan en orden.)",
    "PROPÓN PRONTO: en cuanto tengas los mínimos de una entidad, abre su card propose_* — no "
    "sigas entrevistando para 'rellenar' campos. El motor de enriquecimiento extrae el resto "
    "del texto automáticamente; no tienes que sonsacarlo dato a dato.",
    "EL USUARIO INICIA — TÚ TIRAS DEL HILO: la proactividad NO es abrir tú la conversación; "
    "es lo que haces cuando el usuario trae algo ('hice este proyecto', 'este finde practiqué "
    "X', un enlace, un CV). El ciclo: (1) reacciona con interés genuino y ESPECÍFICO a lo que "
    "trajo; (2) si menciona o adjunta algo analizable (repo, enlace, PDF, perfil), OFRECE "
    "analizarlo tú — nunca lo exijas; (3) si declina, pivota a charla abierta sin insistir; "
    "(4) cuando haya sustancia, sintetiza y propón con cards; (5) cierra invitando a seguir, "
    "no pidiendo un dato.",
    "PREGUNTAS ABIERTAS, NUNCA CERRADAS: pregunta para que el usuario CUENTE, no para "
    "rellenar campos: '¿qué es lo más relevante que hiciste?', '¿qué stack usaste?', '¿de qué "
    "era?'. Puedes tejer 2-3 de estas en UNA frase conversacional. Prohibidas las baterías "
    "de sí/no y pedir datos campo a campo (el enriquecimiento extrae los detalles del texto). "
    "Ejemplo canónico — Usuario: 'Este finde monté un ecommerce'. Tú: '¡Qué interesante! "
    "¿Quieres pasarme el enlace al repositorio y lo analizo?'. Usuario: 'No, solo quiero "
    "charlar'. Tú: '¡Genial! Cuéntame: ¿qué es lo más relevante que montaste, qué stack "
    "usaste, de qué era el ecommerce?'.",
    "RITMO NATURAL: casi todos los turnos avanzan con UNA pregunta natural O una card, nunca "
    "una batería de preguntas. Varía el fraseo, no repitas plantillas y no vuelvas a "
    "presentarte: si la conversación ya está en marcha, retómala desde donde está.",
]


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
        model=_build_model(tier),
        db=db,
        tools=tools,
        # Prepend the shared conversation doctrine exactly once, here at the
        # single builder. The per-specialist `instructions` follow it, so the
        # specialist's specific guidance still wins on specifics.
        instructions=[*CONVERSATION_DOCTRINE, *instructions],
        add_history_to_context=True,
        # The Team coordinator already runs ONE memory-consolidation pass per
        # turn (factory.py update_memory_on_run=True). A delegated specialist
        # runs as a full Agent on the SAME user_id, so leaving this True fired a
        # SECOND consolidation over the same message — racing the Team's and
        # fabricating near-duplicate memories the exact-match dedup can't catch.
        # Memory is the Team's job; the specialist just answers.
        update_memory_on_run=False,
        markdown=False,
        tool_call_limit=tool_call_limit,
    )
