"""Education specialist."""
from __future__ import annotations


def build_education_specialist(*, db):  # type: ignore[no-untyped-def]
    from src.agents.specialists._helpers import build_specialist
    from src.agents.tools.coherence_tools import find_existing
    from src.agents.tools.ui_widgets import propose_education
    from src.agents.tools.universe_writes import upsert_education

    return build_specialist(
        name="education_specialist",
        role="Captura y mantiene educación formal e informal",
        db=db,
        tools=[propose_education, upsert_education, find_existing],
        instructions=[
            "Eres el specialist de educación.",
            "Antes de proponer, usa `find_existing(entity_type='education', query=...)` "
            "para no duplicar instituciones ya capturadas.",
            "Extrae: institución, título (degree), área de estudio (field_of_study), fechas, "
            "si está en curso, highlights.",
            "Si solo te da el nombre de la universidad, pide el título / área antes de proponer.",
            "Llama `propose_education` para confirmar; luego `upsert_education`.",
        ],
    )
