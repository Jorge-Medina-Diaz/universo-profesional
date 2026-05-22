"""Certification specialist."""
from __future__ import annotations


def build_certification_specialist(*, db):  # type: ignore[no-untyped-def]
    from src.agents.specialists._helpers import build_specialist
    from src.agents.tools.coherence_tools import find_existing
    from src.agents.tools.ui_widgets import propose_certification
    from src.agents.tools.universe_writes import upsert_certification

    return build_specialist(
        name="certification_specialist",
        role="Captura certificaciones profesionales",
        db=db,
        tools=[propose_certification, upsert_certification, find_existing],
        instructions=[
            "Eres el specialist de certificaciones.",
            "Antes de proponer, usa `find_existing(entity_type='certification', query=...)`.",
            "Captura: name, issuer, issued_on, expires_on, credential_id, verification_url.",
            "Si el cert tiene caducidad próxima, menciónalo en la propuesta.",
            "Llama `propose_certification` antes de persistir; luego `upsert_certification`.",
        ],
    )
