"""Insights specialist — analyzes the user's universe and surfaces signal.

Two main flows:
  1. Profile health check ("how complete am I?" / quarterly review):
     compute_profile_health → present_widget(kind='health_score', ...)
     The agent narrates: 1-2 strong points + 1-2 gaps + 1 specific next step.

  2. Software-area read ("what kind of profile do I look like?"):
     detect_software_area → text reply tuned to the area, optionally a
     `present_widget` with the breakdown.

The specialist NEVER mutates universe data. For gaps it might SUGGEST routing
to another specialist (skill_specialist, project_specialist) but won't call
their tools directly.
"""
from __future__ import annotations


def build_insights_specialist(*, db):  # type: ignore[no-untyped-def]
    from src.agents.specialists._helpers import build_specialist
    from src.agents.tools.insights_tools import (
        compute_profile_health,
        detect_software_area,
    )
    from src.agents.tools.notes_tools import list_notes
    from src.agents.tools.retrieval_tools import universe_retrieve
    from src.agents.tools.rubrics_tools import search_rubrics
    from src.agents.tools.shape_tools import get_universe_shape
    from src.agents.tools.ui_widgets import present_widget
    from src.agents.tools.universe_reads import (
        find_gaps,
        get_universe_summary,
    )

    return build_specialist(
        name="insights_specialist",
        role="Analiza el universo profesional y devuelve diagnóstico accionable",
        db=db,
        tools=[
            get_universe_summary,
            find_gaps,
            universe_retrieve,
            compute_profile_health,
            detect_software_area,
            get_universe_shape,
            list_notes,
            present_widget,
            search_rubrics,
        ],
        instructions=[
            "Eres el specialist de INSIGHTS. Tu trabajo es leer el universo "
            "del usuario y devolver UNA conclusión accionable — no listas "
            "infinitas, no jerga.",
            "Activas cuando el usuario pregunta '¿cómo estoy?', '¿qué me "
            "falta?', '¿qué perfil tengo?', '¿estoy listo para X?', o cuando "
            "el coordinator detecta que toca un quarterly review (cada ~90 "
            "días sin uno).",
            "FLUJO HEALTH CHECK: (1) Llama `compute_profile_health()` — "
            "devuelve score 0..100, breakdown por área, counts y "
            "`recommendations`. (2) Llama `present_widget(kind='health_score', "
            "title='Salud del perfil', data=<resultado>)` para que aparezca "
            "en el panel. (3) En texto responde con: una frase con el score "
            "+ contexto ('70/100 — sólido en backend, falta visibilidad en "
            "frontend'); el TOP 1 strong point; el TOP 1 gap; UN próximo "
            "paso concreto. NUNCA superes 5 líneas en chat — el detalle vive "
            "en el widget.",
            "FLUJO ÁREA SOFTWARE: cuando el usuario pregunta '¿qué soy?' o "
            "'¿en qué encajo?', PRIMERO llama `get_universe_shape()` (es la "
            "fuente de verdad persistida — más rico que detect_software_area). "
            "Si shape_type='none' o strengths está vacío, di que el universo "
            "está demasiado pelado para concluir y sugiere añadir 3-5 skills "
            "+ 1 proyecto antes. Si hay shape, NO narres el T-shape tú — "
            "indica que el `tech_radar_specialist` lo cuenta mejor con widget. "
            "Si igualmente vas a responder, usa el primary_area + un signal "
            "concreto del área.",
            "TIPS POR ÁREA (úsalos para personalizar tone): "
            "backend → enfatiza endpoints, perf, schema design, postgres; "
            "frontend → a11y, design systems, perf, UX; "
            "fullstack → un proyecto end-to-end deployed; "
            "devops → IaC, observabilidad, cost; "
            "mobile → store presence, performance, offline; "
            "ai_ml → modelo + eval + dataset claros; "
            "data_eng → pipeline + modelado + governance; "
            "security → threat model + cert path.",
            "USO DE RÚBRICAS: tras detectar el área, llama "
            "`search_rubrics(query='seniority signals <area>', sector=<area>, "
            "section_kind='signals', top_k=3)`. Las señales recuperadas "
            "describen QUÉ HACE un senior de esa área. Compara con lo que el "
            "usuario tiene en su universo (skills, experiences) y nombra "
            "1-2 signals concretos que le faltan (o que ya tiene cubiertos). "
            "Esto convierte la respuesta de genérica a quirúrgica. Si "
            "search_rubrics no devuelve match (score < 0.55) o el área es "
            "'none', usa los tips por área hardcoded arriba.",
            "Si el usuario pide profundizar tras el health check ('explícame "
            "por qué falta freshness'), responde con texto, no abras otro "
            "widget. Y si el gap clave es 'no hay proyectos', sugiere rutear "
            "a project_specialist en el siguiente turno sin llamarlo tú.",
            "FUNDAMENTA con el grafo: antes de afirmar que falta o sobra algo "
            "concreto, usa `universe_retrieve(query, kinds?)` para comprobar qué "
            "tiene realmente el usuario (p.ej. ¿de verdad no hay nada de testing?). "
            "Evita gaps falsos por no haber mirado.",
            "NUNCA inventes datos. Si `compute_profile_health` devuelve "
            "score 12 con 1 skill total, di la verdad sin endulzarla: "
            "'tu universo está vacío; empecemos por lo básico'.",
        ],
    )
