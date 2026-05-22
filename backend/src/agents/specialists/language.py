"""Language specialist."""
from __future__ import annotations


def build_language_specialist(*, db):  # type: ignore[no-untyped-def]
    from src.agents.specialists._helpers import build_specialist
    from src.agents.tools.coherence_tools import find_existing
    from src.agents.tools.ui_widgets import propose_language
    from src.agents.tools.universe_writes import upsert_language

    return build_specialist(
        name="language_specialist",
        role="Captura idiomas hablados/escritos con nivel CEFR",
        db=db,
        tools=[propose_language, upsert_language, find_existing],
        instructions=[
            "Eres el specialist de idiomas.",
            "Captura: code (ISO 639-1, 2 letras), name, level (A1..C2, native), certification.",
            "Si dice 'nativo' o 'lengua materna' usa level='native'.",
            "Si dice 'fluido' o 'profesional completo' mapea a C1 o C2.",
            "Llama `propose_language`; luego `upsert_language`. El engine sube el nivel CEFR "
            "automáticamente si el nuevo es superior.",
        ],
    )
