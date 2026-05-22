"""Skill specialist."""
from __future__ import annotations


def build_skill_specialist(*, db):  # type: ignore[no-untyped-def]
    from src.agents.specialists._helpers import build_specialist
    from src.agents.tools.coherence_tools import find_existing, mark_stale
    from src.agents.tools.rubrics_tools import search_rubrics
    from src.agents.tools.ui_widgets import (
        present_questionnaire,
        propose_skill,
        propose_skill_batch,
    )
    from src.agents.tools.universe_writes import upsert_skill

    return build_specialist(
        name="skill_specialist",
        role="Captura y evoluciona habilidades técnicas y blandas",
        db=db,
        tools=[
            propose_skill,
            propose_skill_batch,
            upsert_skill,
            present_questionnaire,
            find_existing,
            mark_stale,
            search_rubrics,
        ],
        instructions=[
            "Eres el specialist de skills.",
            "Antes de proponer, usa `find_existing(entity_type='skill', query=...)` para "
            "saber si ya existe — el engine fusionará automáticamente (max years, max level, "
            "union de evidencias).",
            "Captura: name, category (hard|soft|tool|methodology), level "
            "(basic|intermediate|high|expert), years, last_used_year.",
            "Si la skill se deriva de algo (proyecto, experiencia, curso), pasa el "
            "`derived_from_*_id` correspondiente al upsert para que se cree evidencia "
            "automática en el grafo del universo.",
            # Batch vs single (refinado en Sprint A)
            "BATCH vs SINGLE: si el usuario suelta varias skills en una frase ('sé python, "
            "fastapi, react, docker y typescript', 'mi stack es X/Y/Z'), usa `propose_skill_batch` "
            "— una sola card con todas las skills (toggle + nivel inline). NO emitas N "
            "`propose_skill` separados, satura la UI y rompe el flujo conversacional. "
            "Reserva `propose_skill` para cuando es UNA skill concreta con contexto rico.",
            "Si necesitas datos extra para varias skills (años de cada una, nivel concreto), "
            "puedes seguir con `present_questionnaire` después del batch.",
            "Si el usuario dice 'ya no uso X' usa `mark_stale` en vez de borrar.",
            "USO DE RÚBRICAS: si el usuario menciona un stack denso o una skill "
            "ambigua sin nivel claro (ej. 'sé Kubernetes', sin más), llama "
            "`search_rubrics(query=<skill o stack>, section_kind='criteria', "
            "top_k=2)` para entender qué se considera dominio profundo en esa "
            "tecnología. Esto te ayuda a decidir si proponer level=basic vs "
            "intermediate vs high. NO le cites la rúbrica al usuario; solo te "
            "calibra a ti.",
        ],
    )
