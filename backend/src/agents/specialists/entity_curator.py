"""Entity curator — experimental generalist specialist (R13).

Instead of routing to one specialist per universe entity kind, this single
agent captures ANY supported entity via the generic `propose_entity` tool. It
is registered ALONGSIDE the per-entity specialists behind
`agents_entity_curator_enabled` (default OFF), so we can A/B the consolidated
routing surface before removing the per-entity specialists. The generic tool
goes through the SAME HITL + coherence path as the per-entity `propose_*`
tools (proposal_id injected server-side, resolved via /proposals/{id}/resolve).
"""
from __future__ import annotations

from typing import Any


def build_entity_curator(*, db: Any):  # type: ignore[no-untyped-def]
    from src.agents.specialists._helpers import build_specialist  # noqa: PLC0415
    from src.agents.tools.coherence_tools import find_existing  # noqa: PLC0415
    from src.agents.tools.discovery_tools import (  # noqa: PLC0415
        get_profile_completeness,
    )
    from src.agents.tools.ui_widgets import (  # noqa: PLC0415
        present_questionnaire,
        propose_entity,
    )

    return build_specialist(
        name="entity_curator",
        role=(
            "Captura cualquier entidad profesional individual (experiencia, "
            "formación, proyecto, skill, certificación, curso, idioma, logro, "
            "interés, artefacto, decisión de arquitectura) en una sola card HITL"
        ),
        db=db,
        tools=[propose_entity, find_existing, get_profile_completeness, present_questionnaire],
        instructions=[
            "Eres el curador de entidades: un generalista que captura UNA entidad "
            "profesional a la vez. No eres un formulario; conversas para extraer la "
            "historia y luego propones la captura.",
            # Context-before-capture (same discipline as the per-entity specialists)
            "ANTES DE PROPONER: llama `find_existing(entity_type=...)` para ver si la "
            "entidad ya existe. Si el usuario menciona algo conocido, es una "
            "actualización — el engine de coherencia fusiona automáticamente.",
            # The single generic capture tool
            "CAPTURA: usa `propose_entity(entity_type, payload)`. `entity_type` DEBE "
            "ser uno de: experience, education, project, skill, certification, course, "
            "language, achievement, interest, artifact, architecture_decision. "
            "`payload` es el dict de campos de ese tipo (misma forma que tendría el "
            "`propose_<tipo>` específico): p.ej. experience → {organization, role, "
            "start_date, end_date, is_current, description, highlights, competences}; "
            "skill → {name, category (hard|soft|tool|methodology), level, years}; "
            "language → {code, name, level}; certification → {name, issuer, issued_on}.",
            "NUNCA inventes un entity_type fuera de la lista. Si la intención del "
            "usuario no encaja en ninguno (p.ej. una meta o una nota narrativa), dilo "
            "claramente y NO llames `propose_entity` — esos casos los gestionan otros "
            "flujos.",
            # One entity per turn, conversational (rhythm handled by the shared doctrine)
            "UNA entidad por turno. Para varias entidades dictadas/importadas a la vez "
            "NO emitas N propuestas: eso es ingesta en bloque y la gestiona otro flujo.",
            "Tras proponer, resume brevemente y ofrece el siguiente paso natural.",
        ],
    )
