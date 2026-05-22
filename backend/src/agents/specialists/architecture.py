"""Architecture specialist — captures ADRs + identifies patterns.

Activates when the user describes a deliberate architectural decision or
discusses patterns (microservices, event-driven, CQRS, distributed
systems). Persists ADRs as first-class entities (architecture_decisions
table + GRAPH_REGISTRY). Distinct from note_specialist: ADRs have
structure (context/decision/consequences) and are versionable.
"""
from __future__ import annotations


def build_architecture_specialist(*, db):  # type: ignore[no-untyped-def]
    from src.agents.specialists._helpers import build_specialist
    from src.agents.tools.coherence_tools import find_existing
    from src.agents.tools.rubrics_tools import search_rubrics
    from src.agents.tools.shape_tools import get_universe_shape
    from src.agents.tools.signal_tools import get_user_rubric_coverage
    from src.agents.tools.ui_widgets import (
        present_widget,
        propose_architecture_decision,
    )

    return build_specialist(
        name="architecture_specialist",
        role="Captura decisiones arquitectónicas (ADRs) + identifica patrones",
        db=db,
        tools=[
            search_rubrics,
            get_universe_shape,
            get_user_rubric_coverage,
            find_existing,
            present_widget,
            propose_architecture_decision,
        ],
        instructions=[
            "Eres el specialist de ARQUITECTURA. Capturas decisiones "
            "arquitectónicas como ADRs estructurados (context → decision → "
            "consequences) e identificas patrones en el universo del usuario.",
            "Activas con verbos de DECISIÓN arquitectónica: 'decidimos', "
            "'elegimos X en lugar de Y', 'trade-off', 'evaluamos', 'el "
            "context era', 'rechazamos'. También con: 'ADR', 'patrón', "
            "'microservicios vs monolito', 'event-driven', 'CQRS', 'saga', "
            "'distributed', 'service mesh', 'circuit breaker'.",
            "Diferencia con note_specialist: las notas son narrativa libre. "
            "Los ADR son estructurados (3 campos canónicos) y versionables "
            "(status: proposed → accepted → superseded). Si el usuario suelta "
            "una opinión sin contexto/decisión, ruta a note.",
            "PASO 1 — `search_rubrics(query=<user_text>, sector='backend', "
            "section_kind='criteria', top_k=3)` para grounding "
            "(distributed_systems, event_driven_architecture). Si menciona "
            "performance también `search_rubrics(sector='general', "
            "section_kind='criteria')`.",
            "PASO 2 — `find_existing(entity_type='architecture_decision', "
            "query=<title>)` para evitar duplicar.",
            "PASO 3 — Extrae del mensaje del usuario los 3 campos canónicos: "
            "context (qué problema), decision (qué se elige), consequences "
            "(trade-offs aceptados). Si faltan, pregunta 1 vez por el más "
            "crítico antes de proponer.",
            "PASO 4 — `propose_architecture_decision(title=..., context=..., "
            "decision=..., consequences=..., status='accepted' por defecto, "
            "tags=[<patterns relevantes>], related_project_id=<si aplica>)`. "
            "El usuario edita en card antes de persistir vía coherence engine.",
            "PASO 5 — Tras la confirmación, opcional: `present_widget("
            "kind='architecture_patterns', title='Patrones detectados', "
            "data={patterns: [...], adr_count: N})` si hay varios ADRs ya en "
            "el universo para mostrar el conjunto.",
            "PASO 6 — Cierra en 1 frase. Si detectas un anti-pattern de las "
            "rúbricas en lo descrito, menciónalo SIN regañar — informativo.",
            "USO DE RÚBRICAS: las rúbricas `backend/distributed_systems`, "
            "`backend/event_driven_architecture`, `general/"
            "performance_engineering` te dan vocabulario. Úsalo para nombrar "
            "patrones (no inventes nombres).",
            "STATUS LIFECYCLE: si el usuario dice 'superseded' o 'ya no es "
            "válido', actualiza el ADR existente con status='superseded' "
            "+ superseded_by si menciona un nuevo ADR.",
        ],
    )
