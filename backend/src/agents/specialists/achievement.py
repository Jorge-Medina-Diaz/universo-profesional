"""Achievement specialist."""
from __future__ import annotations


def build_achievement_specialist(*, db):  # type: ignore[no-untyped-def]
    from src.agents.specialists._helpers import build_specialist
    from src.agents.tools.coherence_tools import find_existing
    from src.agents.tools.shape_tools import upsert_artifact
    from src.agents.tools.ui_widgets import propose_achievement, propose_artifact
    from src.agents.tools.universe_writes import upsert_achievement

    return build_specialist(
        name="achievement_specialist",
        role="Captura logros, premios, publicaciones y reconocimientos",
        db=db,
        tools=[
            propose_achievement,
            upsert_achievement,
            find_existing,
            propose_artifact,
            upsert_artifact,
        ],
        instructions=[
            "Eres el specialist de achievements.",
            "Captura: title, achieved_on, description, context, evidence_url.",
            "Si suena a publicación, patente o premio, usa este path en vez de skill o experience.",
            "Llama `propose_achievement`; luego `upsert_achievement`.",
            "ARTIFACT: si el logro tiene URL pública (paper publicado, post oficial del "
            "premio, vídeo de la talk ganadora), ofrece `propose_artifact` adicional con "
            "el type correcto (paper|talk|video|other). El upsert_artifact se llama tras "
            "confirmación. Logros sin URL pública se quedan como achievement plano.",
        ],
    )
