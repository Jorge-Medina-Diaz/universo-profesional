"""Course specialist."""
from __future__ import annotations


def build_course_specialist(*, db):  # type: ignore[no-untyped-def]
    from src.agents.specialists._helpers import build_specialist
    from src.agents.tools.coherence_tools import find_existing
    from src.agents.tools.ui_widgets import propose_course
    from src.agents.tools.universe_writes import upsert_course

    return build_specialist(
        name="course_specialist",
        role="Captura cursos y formaciones (online u offline)",
        db=db,
        tools=[propose_course, upsert_course, find_existing],
        instructions=[
            "Eres el specialist de cursos.",
            "Antes de proponer, usa `find_existing(entity_type='course', query=...)`.",
            "Captura: title, platform, started_on, completed_on, duration_hours, certificate_url.",
            "Marca como en curso (sin completed_on) si el usuario sigue tomándolo.",
            "Cuando el usuario diga 'completé X', haz upsert con `completed_on` — el engine "
            "respeta el `completed_on` existente y solo actualiza si todavía estaba en curso.",
        ],
    )
