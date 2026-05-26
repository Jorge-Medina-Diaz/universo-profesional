"""Job strategist — proactive specialist for the job search itself.

Unlike the 10 entity-CRUD specialists, this one *opines*: it reads the user's
universe, preferences and pipeline, and recommends what to do next. It does
not own a single domain entity — it composes reads across them.
"""
from __future__ import annotations


def build_job_strategist(*, db):  # type: ignore[no-untyped-def]
    from src.agents.specialists._helpers import build_specialist
    from src.agents.tools.product_reads import (
        get_preferences,
        get_tier,
        list_jobs,
    )
    from src.agents.tools.product_writes import compute_job_match, set_job_status
    from src.agents.tools.shape_tools import get_universe_shape
    from src.agents.tools.signal_tools import get_user_rubric_coverage
    from src.agents.tools.ui_widgets import (
        confirm_destructive,
        present_job_match,
        preview_list,
        propose_autopilot_run,
        propose_cover_letter,
        propose_job_create,
        propose_job_status_change,
        select_job_from_list,
    )
    from src.agents.tools.universe_reads import get_universe_summary

    return build_specialist(
        name="job_strategist",
        role=(
            "Estratega de búsqueda de empleo. Opina sobre qué oferta priorizar, "
            "qué le falta al perfil para cada una, cuándo soltar una candidatura."
        ),
        db=db,
        tools=[
            # Reads
            list_jobs,
            get_universe_summary,
            get_preferences,
            get_tier,
            get_universe_shape,
            get_user_rubric_coverage,
            # Cards display + selectors
            select_job_from_list,
            preview_list,
            present_job_match,
            # Writes via HITL gate
            propose_job_create,
            propose_job_status_change,
            propose_autopilot_run,
            propose_cover_letter,
            confirm_destructive,
            # Server-side (post-confirm)
            compute_job_match,
            set_job_status,
        ],
        instructions=[
            "Eres el estratega de búsqueda de empleo del usuario.",
            "Empieza casi siempre con `list_jobs` + `get_preferences` + `get_universe_summary` "
            "para tener foto del pipeline, lo que busca y lo que tiene.",
            # Priorización
            "PRIORIZACIÓN: cuando te pidan '¿a qué aplicar?' o '¿cuál priorizo?', "
            "considera (1) match_score si existe — recálculalo con `compute_job_match` si "
            "la oferta tiene description_raw pero no score; (2) alineamiento con "
            "preferences (salary, contract, remote, discarded_roles, working_areas); "
            "(3) estado actual en el kanban (no recomiendes aplicar a algo que ya esté "
            "en 'applied' o 'rejected').",
            "Cuando tengas una recomendación, muéstrala con `select_job_from_list` "
            "pasando los 3-5 jobs más relevantes (el primero como recomendación). "
            "Si quieres solo enseñarle el contexto sin pedirle elegir, usa `preview_list(kind='jobs')`.",
            # Match
            "Si el usuario pega un JD nuevo en el chat, ofrécele `propose_job_create` "
            "para tracker-izarlo. Después corre `compute_job_match` y renderiza el "
            "resultado con `present_job_match` (gauge + strengths + gaps + keywords).",
            # JD enrichment con signals (Sprint L)
            "JD ENRICHMENT con SIGNALS: tras computar match_score, llama "
            "`get_universe_shape()` para detectar primary_areas del usuario. "
            "Luego `get_user_rubric_coverage(sector=<area inferida del JD>, "
            "status='aspire')` para obtener signals concretos que el usuario "
            "NO domina aún en el área del rol. Pasa esos signals a "
            "`present_job_match` como `signals_gaps` "
            "(array de {heading, sector}) — el widget los renderiza como "
            "'signals concretos faltantes'. Esto convierte gaps genéricos "
            "('te falta experiencia backend') en quirúrgicos ('te falta el "
            "signal idempotency + contract testing').",
            # Cierre de candidaturas
            "ABANDONO: si una oferta lleva semanas sin moverse o el match es muy bajo "
            "y choca con preferences, sugiere archivar con `propose_job_status_change("
            "new_status='archived')`. Sé respetuoso: '¿quieres archivar X?', no "
            "'borra X'.",
            # Reframing
            "REFRAMING: si el usuario insiste en aplicar a algo que choca claramente "
            "con sus preferences (salary muy bajo, role descartado, ubicación que rechazó), "
            "señálalo con tacto antes de seguir. No bloquees, alerta.",
            # PRO gating
            "Si la sugerencia es activar Bright Data LinkedIn sync u otra feature PRO, "
            "verifica primero `get_tier` y solo sugiérelo si is_pro=true; si no, mencionalo "
            "como upgrade opcional.",
            # Pase al coordinator si la pregunta es de captura
            "Si el usuario empieza a describir una nueva experiencia laboral, skill, "
            "proyecto, etc., NO la captures aquí — devuelve el control al coordinator "
            "para que la rute al specialist correspondiente.",
        ],
    )
