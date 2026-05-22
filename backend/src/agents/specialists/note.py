"""Note specialist — captures freeform narrative biographical content.

Activates when the user shares context that isn't a discrete universe entity:
learning threads, opinions, ongoing project narratives, work style, beliefs.
The specialist liberally tags so the curator and CV generator can later filter.
"""
from __future__ import annotations


def build_note_specialist(*, db):  # type: ignore[no-untyped-def]
    from src.agents.specialists._helpers import build_specialist
    from src.agents.tools.knowledge_tools import search_knowledge
    from src.agents.tools.notes_tools import add_note, list_notes, update_note

    return build_specialist(
        name="note_specialist",
        role="Captura narrativa biográfica no estructurada (notas, opiniones, threads)",
        db=db,
        tools=[add_note, update_note, list_notes, search_knowledge],
        instructions=[
            "Eres el specialist de notas — el archivo personal del usuario.",
            "Activas cuando el usuario comparte algo que NO es una entidad rígida del universo: ",
            "'estoy estudiando X', 'me gusta el enfoque Y', 'estas semanas he leído estos papers'.",
            "Captura como Note markdown breve y tag liberalmente. Tags útiles: 'learning', "
            "'opinion', 'wip', 'paper', 'reading-thread-YYYY-MM', dominio (e.g. 'rag', 'ml', 'frontend').",
            "Si el contenido también encaja con una entidad (project, skill), no compitas — el "
            "coordinator routeará al specialist correspondiente. Tú captas el contexto narrativo.",
            "Si el usuario menciona varios papers/lecturas, sugiere usar `propose_pdf_import` si "
            "quiere subirlos al knowledge base (cuando esté wired).",
            "Antes de proponer una nueva nota sobre el mismo tema, considera `list_notes(tag=...)` "
            "para añadir contenido a una existente vía `update_note` en lugar de crear duplicados.",
        ],
    )
