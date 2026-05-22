"""Work-experience specialist."""
from __future__ import annotations


def build_experience_specialist(*, db):  # type: ignore[no-untyped-def]
    from src.agents.specialists._helpers import build_specialist
    from src.agents.tools.coherence_tools import find_existing, get_change_history
    from src.agents.tools.shape_tools import upsert_artifact
    from src.agents.tools.ui_widgets import propose_artifact, propose_experience
    from src.agents.tools.universe_writes import upsert_experience

    return build_specialist(
        name="experience_specialist",
        role="Captura y mantiene experiencias laborales con coherencia temporal",
        db=db,
        tools=[
            propose_experience,
            upsert_experience,
            find_existing,
            get_change_history,
            propose_artifact,
            upsert_artifact,
        ],
        instructions=[
            "Eres el specialist de experiencia laboral.",
            "Antes de proponer, considera usar `find_existing` (entity_type='experience') "
            "para detectar si el usuario está actualizando una experiencia ya capturada.",
            "Extrae: organización, rol, fechas (mes/año), si es actual, 1-3 highlights medibles, "
            "1-5 competences relevantes.",
            "Si faltan datos críticos (organización o rol), pregunta. No inventes.",
            "Cuando tengas los datos mínimos, llama `propose_experience` para que el usuario "
            "confirme en una card. Tras la confirmación, llama `upsert_experience`.",
            "Si el usuario dice 'cambié de empleo' o menciona que terminó algo, también haz "
            "upsert con el `end_date` correcto — el engine sabrá flippar `is_current=false`.",
            "ARTIFACT: si el usuario menciona algo público derivado de este puesto (talk "
            "que dio representando a la empresa, blog en el engineering blog, paper "
            "coautorizado), ofrece `propose_artifact` con type apropiado tras persistir "
            "la experience. Confirma luego con `upsert_artifact`.",
        ],
    )
