"""Interest specialist."""
from __future__ import annotations


def build_interest_specialist(*, db):  # type: ignore[no-untyped-def]
    from src.agents.specialists._helpers import build_specialist
    from src.agents.tools.coherence_tools import find_existing
    from src.agents.tools.ui_widgets import propose_interest
    from src.agents.tools.universe_writes import upsert_interest

    return build_specialist(
        name="interest_specialist",
        role="Captura y evoluciona intereses profesionales/personales",
        db=db,
        tools=[propose_interest, upsert_interest, find_existing],
        instructions=[
            "Eres el specialist de intereses.",
            "Captura: name, description (qué le motiva o cómo lo aplica).",
            "Solo intereses con peso profesional (ML, diseño, OSS, mentoring, etc.).",
            "Cuando el usuario amplíe sobre un interés ya capturado, haz upsert — el engine "
            "concatena las descripciones nuevas en lugar de pisarlas.",
        ],
    )
