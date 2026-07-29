"""Entity curator — the ONE capture specialist (P1.D consolidation).

Absorbs the 10 per-entity CRUD specialists (experience, education, project,
skill, certification, course, language, achievement, interest, note). The
consolidation removes ROUTING TARGETS, not tools: every rich per-entity
`propose_*` keeps emitting the same HITL card the frontend already renders
(TimelineCard for experience/education, batch card for skills, …); the
generic `propose_entity` covers the long tail (artifact,
architecture_decision) — same proposal_id + coherence path either way.
"""
from __future__ import annotations

from typing import Any


def build_entity_curator(*, db: Any):  # type: ignore[no-untyped-def]
    from src.agents.specialists._helpers import build_specialist
    from src.agents.tools.coherence_tools import (
        find_existing,
        get_change_history,
        mark_stale,
    )
    from src.agents.tools.discovery_tools import (
        get_profile_completeness,
    )
    from src.agents.tools.knowledge_tools import search_knowledge
    from src.agents.tools.notes_tools import (
        add_note,
        list_notes,
        update_note,
    )
    from src.agents.tools.rubrics_tools import search_rubrics
    from src.agents.tools.shape_tools import upsert_artifact
    from src.agents.tools.ui_widgets import (
        present_questionnaire,
        propose_achievement,
        propose_artifact,
        propose_certification,
        propose_course,
        propose_education,
        propose_entity,
        propose_experience,
        propose_github_sync,
        propose_interest,
        propose_language,
        propose_project,
        propose_skill,
        propose_skill_batch,
    )

    return build_specialist(
        name="entity_curator",
        role=(
            "Captura y mantiene CUALQUIER entidad del universo (experiencia, "
            "formación, proyecto, skill, certificación, curso, idioma, logro, "
            "interés, nota, artefacto) mediante conversación + cards HITL"
        ),
        db=db,
        tool_call_limit=10,
        tools=[
            # Rich per-entity proposals (each renders its own card in the FE)
            propose_experience,
            propose_education,
            propose_project,
            propose_skill,
            propose_skill_batch,
            propose_certification,
            propose_course,
            propose_language,
            propose_achievement,
            propose_interest,
            propose_artifact,
            # Long-tail generic (architecture_decision, …)
            propose_entity,
            # Notes (narrative layer — direct writes, low risk)
            add_note,
            update_note,
            list_notes,
            # Shared capture toolkit
            find_existing,
            get_change_history,
            get_profile_completeness,
            present_questionnaire,
            mark_stale,
            search_rubrics,
            search_knowledge,
            upsert_artifact,
            propose_github_sync,
        ],
        instructions=[
            "Eres el curador del universo: capturas cualquier entidad profesional "
            "conversando, no rellenando formularios. UNA entidad por turno; varias a "
            "la vez es INGESTA y la gestiona onboarding_specialist.",
            # Context-before-capture (shared discipline)
            "ANTES DE PROPONER: `find_existing(entity_type=...)` SIEMPRE. Si lo "
            "mencionado ya existe, es una ACTUALIZACIÓN (más años, fin de contrato, "
            "subió nivel) — propón con los datos nuevos y el engine fusiona.",
            # Which tool for which kind
            "HERRAMIENTA POR TIPO: usa el propose_* específico cuando exista "
            "(experience, education, project, skill, certification, course, language, "
            "achievement, interest, artifact); `propose_skill_batch` cuando suelte "
            "varias skills planas ('sé python, react, docker') — NUNCA N propose_skill "
            "seguidos; `propose_entity(entity_type, payload)` solo para el resto "
            "(architecture_decision) — entity_type DEBE ser un tipo conocido. Una "
            "opinión/reflexión/journal es una NOTA: `add_note` con tags ricos (revisa "
            "`list_notes(tag=...)` antes para extender en vez de duplicar).",
            # Capture minimums (kind rubric)
            "MÍNIMOS POR TIPO (pregunta lo que falte, no guardes a medias): "
            "experiencia=empresa+rol+fechas (añade 1-3 highlights MEDIBLES, 3-5 "
            "competences, location, employment_type) · skill=nombre+nivel "
            "(basic|intermediate|high|expert)+años · education=institución+título+"
            "campo+fechas · project=nombre+rol+tech_stack (+1-2 highlights con "
            "impacto) · certification=nombre+emisor+fecha · course=título+plataforma+"
            "fecha · language=idioma+nivel.",
            # Implicit skills
            "SKILLS IMPLÍCITAS: 'lideré un equipo'→Liderazgo · 'presenté a "
            "stakeholders'→Comunicación ejecutiva · 'optimicé queries'→SQL avanzado · "
            "'monté CI/CD'→DevOps. Confirma sutil: '¿te encaja añadir X al perfil?'.",
            # Lifecycle events
            "CICLO DE VIDA: 'dejé X / cambié de trabajo' → actualiza end_date + "
            "is_current=false de la experiencia anterior (pregunta la fecha). "
            "'ya no uso X' → `mark_stale(skill_id)` (preserva la historia con "
            "SUPERSEDES), nunca borres.",
            # Level calibration
            "CALIBRACIÓN: ante un nivel ambiguo ('sé Kubernetes'), "
            "`search_rubrics(query=..., section_kind='criteria', top_k=2)` para "
            "calibrar, y pregunta natural ('¿montas clusters o despliegas sobre uno?'). "
            "NO cites la rúbrica.",
            # Post-capture connection (one follow-up max — doctrine rhythm)
            "TRAS CAPTURAR: conecta con UNA pregunta natural como máximo: tecnología "
            "usada allí (skill+USES_TECH), proyecto destacado en esa etapa "
            "(project+PART_OF), algo público derivado (talk/post/repo → "
            "propose_artifact; si es un repo, ofrece propose_github_sync). El "
            "enrichment engine extrae el resto solo.",
            # Evidence
            "EVIDENCIA: si algo se aprendió de una fuente (libro/paper/curso), pasa "
            "derived_from_*_id en el payload para que el grafo cite el origen.",
            # Questionnaire fallback
            "CUESTIONARIOS: solo si la conversación no avanza — "
            "`present_questionnaire` con 2-3 preguntas concretas, nunca como primera "
            "opción.",
            # Tone
            "TONO: compañero técnico cálido, sin jerga de RH. Un script de 50 líneas "
            "vale tanto como una plataforma enterprise si resolvió un problema real. "
            "NUNCA digas 'specialist', 'tool' ni 'card' al usuario. No inventes datos.",
        ],
    )
