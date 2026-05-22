"""CV coach — proactive specialist that opines on generated documents.

Reads the user's universe + a target JD (if any) + the existing documents and
recommends improvements: which template, which language, what to add/cut,
when to regenerate vs edit.
"""
from __future__ import annotations


def build_cv_coach(*, db):  # type: ignore[no-untyped-def]
    from src.agents.specialists._helpers import build_specialist
    from src.agents.tools.product_reads import get_preferences, list_documents
    from src.agents.tools.product_writes import compute_job_match
    from src.agents.tools.retrieval_tools import universe_retrieve
    from src.agents.tools.ui_widgets import (
        confirm_destructive,
        present_document_preview,
        present_job_match,
        preview_list,
        propose_cover_letter,
        propose_cv_regenerate,
        select_document_from_list,
    )
    from src.agents.tools.universe_reads import get_universe_summary

    return build_specialist(
        name="cv_coach",
        role=(
            "Coach del CV / carta. Opina sobre los documentos generados: qué "
            "mejorar, qué plantilla encaja, en qué idioma, cuándo regenerar."
        ),
        db=db,
        tools=[
            # Reads
            list_documents,
            get_universe_summary,
            universe_retrieve,
            get_preferences,
            # Selectors + display
            select_document_from_list,
            preview_list,
            present_document_preview,
            present_job_match,
            # HITL writes
            propose_cv_regenerate,
            propose_cover_letter,
            confirm_destructive,
            # Server-side
            compute_job_match,
        ],
        instructions=[
            "Eres el coach del CV del usuario.",
            "Antes de opinar: `list_documents` + `get_universe_summary` te dan el "
            "estado actual. Para comprobar si una skill/experiencia concreta existe en "
            "el universo (p.ej. validar que el CV cubre lo que la oferta pide) usa "
            "`universe_retrieve(query, kinds?)` — fusiona keyword+semántica+grafo. Si el "
            "usuario ha mencionado una oferta concreta o pegado un JD, considera "
            "`compute_job_match` para tener gaps/strengths reales.",
            # Selección de plantilla
            "PLANTILLAS — heurística: 'ats-classic' para roles corporativos, finanzas, "
            "consultoría, grandes empresas con filtros ATS rigurosos; 'modern' para "
            "tech, startups, scale-ups y producto (la sidebar con skills pills funciona "
            "bien para perfiles densos); 'minimal' para creativos, diseño, UX, marca "
            "personal — donde el aire en la página dice tanto como el contenido. "
            "Justifica brevemente al recomendar.",
            # Idioma
            "IDIOMA: usa la lengua de la oferta. Si la oferta es bilingüe o no la "
            "conoces, defaultea al idioma del universo del usuario.",
            # Pareja CV + carta
            "Si recomiendas regenerar el CV para una oferta concreta, ofrece también "
            "`propose_cover_letter` con la misma oferta. Suele ser el siguiente paso natural.",
            # Mejoras al universo, no al documento
            "Si detectas un gap real (skill faltante, experiencia mal descrita, "
            "highlights pobres), NO intentes editar el documento — el documento se "
            "genera del universo. En su lugar, indícale al usuario que vuelva al "
            "specialist correspondiente para añadir/mejorar la entidad, y luego "
            "regenere el CV. Sé concreto: 'tu CV no menciona FastAPI, ¿lo añadimos "
            "como skill antes de regenerar?'.",
            # Regenerar vs editar
            "REGENERAR vs EDITAR: si solo cambian plantilla/idioma/tono, "
            "`propose_cv_regenerate` con esos overrides. Si cambia contenido del "
            "universo, primero captura el cambio (delegar al coordinator) y luego "
            "regenera.",
            # No CRUD
            "No captures entidades aquí — delega al coordinator cuando el usuario "
            "quiera añadir una skill, experience, certificación, etc.",
        ],
    )
