"""Build the Agno team that drives chat-first universe capture.

The factory is the single composition root for agents: pick the LLM provider,
load the 9 specialists (one per universe entity) + a routing coordinator,
expose the result. We build the team once (lru_cache) and reuse it for every
request — Agno's `Team` is stateless (state lives in the configured DB), so
concurrent requests are safe.
"""
from __future__ import annotations

from functools import lru_cache
from typing import Literal

from src.shared.config import get_settings
from src.shared.db import get_engine

ModelTier = Literal["coordinator", "specialist"]

# Output cap per run. Routing + most card-emitting turns are short; this
# bounds runaway generation cost without truncating normal replies.
_MAX_TOKENS = 4096
# Low (but non-zero — Agno treats 0.0 as "unset") temperature for the
# coordinator so routing is near-deterministic; specialists get a touch
# more room for natural phrasing.
_TEMPERATURE_BY_TIER: dict[str, float] = {"coordinator": 0.1, "specialist": 0.3}


def _build_model(tier: ModelTier = "coordinator"):  # type: ignore[no-untyped-def]
    """Pick a model instance for the given tier.

    Model tiering (the whole point of having a coordinator + cheap
    specialists): the coordinator routes and reasons → strong model
    (`agents_coordinator_model`, e.g. Sonnet); the 25 specialists work on
    small, focused payloads → cheap/fast model (`agents_specialist_model`,
    e.g. Haiku). Both fall back to a shim mock when no API key is
    configured so dev/test boot even offline.
    """
    settings = get_settings()
    provider = settings.agents_provider_resolved
    if provider == "anthropic":
        from agno.models.anthropic import Claude

        # Repair empty content blocks before they reach Anthropic (see module
        # docstring): agno's formatter can emit empty text blocks during route
        # hand-offs, which 400s the whole request.
        from src.agents.infra.anthropic_sanitize import install_anthropic_sanitizer

        install_anthropic_sanitizer()

        model_id = (
            settings.agents_coordinator_model
            if tier == "coordinator"
            else settings.agents_specialist_model
        )
        # Enable Anthropic prompt caching for the system prompt + tool defs.
        # System prompts repeat verbatim turn after turn; caching them cuts
        # input-token cost ~70% on busy chats. `cache_system_prompt` covers
        # the team-level instructions; `cache_tools` covers the tool schema.
        return Claude(
            id=model_id,
            api_key=settings.anthropic_api_key,
            cache_system_prompt=True,
            cache_tools=True,
            temperature=_TEMPERATURE_BY_TIER[tier],
            max_tokens=_MAX_TOKENS,
        )
    if provider == "openai":
        from agno.models.openai import OpenAIChat

        model_id = "gpt-4o" if tier == "coordinator" else "gpt-4o-mini"
        return OpenAIChat(
            id=model_id,
            api_key=settings.openai_api_key,
            temperature=_TEMPERATURE_BY_TIER[tier],
            max_tokens=_MAX_TOKENS,
        )
    # Mock: OpenAI-compatible client pointed at an unreachable URL. The chat
    # surface boots and tool wiring works; actual LLM calls fail loudly,
    # signalling the user to configure ANTHROPIC_API_KEY or OPENAI_API_KEY.
    from agno.models.openai import OpenAILike

    return OpenAILike(id="mock-model", api_key="mock", base_url="http://localhost:1/v1")


def _build_db():  # type: ignore[no-untyped-def]
    """Reuse the app's AsyncEngine for Agno's session/memory storage."""
    from agno.db.postgres.async_postgres import AsyncPostgresDb

    return AsyncPostgresDb(
        db_engine=get_engine(),
        session_table="agno_sessions",
        memory_table="agno_memories",
        knowledge_table="agno_knowledge_chunks",
        create_schema=True,
    )


@lru_cache(maxsize=1)
def get_universe_team():  # type: ignore[no-untyped-def]
    """Return the cached universe coordinator team."""
    from agno.team import Team

    from src.agents.specialists.achievement import build_achievement_specialist
    from src.agents.specialists.agent_system import build_agent_system_specialist
    from src.agents.specialists.architecture import build_architecture_specialist
    from src.agents.specialists.certification import build_certification_specialist
    from src.agents.specialists.cloud_posture import build_cloud_posture_specialist
    from src.agents.specialists.course import build_course_specialist
    from src.agents.specialists.curiosity import build_curiosity_specialist
    from src.agents.specialists.cv_coach import build_cv_coach
    from src.agents.specialists.data_engineering import build_data_engineering_specialist
    from src.agents.specialists.education import build_education_specialist
    from src.agents.specialists.experience import build_experience_specialist
    from src.agents.specialists.goals import build_goals_specialist
    from src.agents.specialists.insights import build_insights_specialist
    from src.agents.specialists.interest import build_interest_specialist
    from src.agents.specialists.interview_prep import build_interview_prep_specialist
    from src.agents.specialists.job_strategist import build_job_strategist
    from src.agents.specialists.language import build_language_specialist
    from src.agents.specialists.note import build_note_specialist
    from src.agents.specialists.onboarding import build_onboarding_specialist
    from src.agents.specialists.portfolio import build_portfolio_specialist
    from src.agents.specialists.project import build_project_specialist
    from src.agents.specialists.security_posture import build_security_posture_specialist
    from src.agents.specialists.skill import build_skill_specialist
    from src.agents.specialists.tech_radar import build_tech_radar_specialist
    from src.agents.tools.coherence_tools import (
        find_existing,
        get_change_history,
        get_recent_activity,
        list_pending_curation,
    )
    from src.agents.tools.curiosity_tools import get_domain_template
    from src.agents.tools.insights_tools import (
        compute_profile_health,
        detect_software_area,
    )
    from src.agents.tools.knowledge_tools import search_knowledge
    from src.agents.tools.notes_tools import list_notes
    from src.agents.tools.rubrics_tools import list_rubric_sectors, search_rubrics
    from src.agents.tools.shape_tools import (
        get_universe_shape,
        list_artifacts,
        recompute_universe_shape,
    )
    from src.agents.tools.signal_tools import (
        get_user_rubric_coverage,
        recompute_user_signals,
    )
    from src.agents.tools.ui_widgets import (
        confirm_destructive,
        present_document_preview,
        present_graph_view,
        present_job_match,
        present_progress,
        present_questionnaire,
        preview_list,
        propose_brightdata_sync,
        propose_cover_letter,
        propose_github_sync,
        propose_pdf_import,
        set_chat_focus,
        upload_document_inline,
    )
    from src.agents.tools.universe_reads import (
        find_gaps,
        get_universe_summary,
    )
    # Sprint O — hybrid graph retrieval (BM25 + dense + PPR + RRF).
    from src.agents.tools.retrieval_tools import (
        enrich_universe,
        explain_path,
        get_career_pillars,
        get_graph_neighbors,
        universe_retrieve,
    )

    db = _build_db()
    members = [
        # 10 entity-CRUD specialists
        build_experience_specialist(db=db),
        build_education_specialist(db=db),
        build_project_specialist(db=db),
        build_skill_specialist(db=db),
        build_certification_specialist(db=db),
        build_course_specialist(db=db),
        build_language_specialist(db=db),
        build_achievement_specialist(db=db),
        build_interest_specialist(db=db),
        build_note_specialist(db=db),
        # 2 proactive specialists (Sprint B)
        build_job_strategist(db=db),
        build_cv_coach(db=db),
        # Curiosity specialist (Sprint D — deep dives)
        build_curiosity_specialist(db=db),
        # Sprint E — goals, insights, interview prep, onboarding
        build_goals_specialist(db=db),
        build_insights_specialist(db=db),
        build_interview_prep_specialist(db=db),
        build_onboarding_specialist(db=db),
        # Sprint F — polyglot foundation: shape + LLM agents vertical
        build_agent_system_specialist(db=db),
        build_tech_radar_specialist(db=db),
        # Sprint H — cloud + platform vertical
        build_cloud_posture_specialist(db=db),
        # Sprint I — data engineering vertical
        build_data_engineering_specialist(db=db),
        # Sprint J — security vertical
        build_security_posture_specialist(db=db),
        # Sprint K — architecture vertical
        build_architecture_specialist(db=db),
        # Sprint L — portfolio capstone (consumes all the above)
        build_portfolio_specialist(db=db),
    ]

    instructions = [
        # Identity + tone
        "Eres el compañero agéntico que entiende, estructura y MANTIENE el universo "
        "profesional del usuario a lo largo del tiempo — un razonador con persistencia "
        "inteligente, no un formulario con chat. Idioma por defecto: español (cambia a "
        "inglés si lo piden). Tono cercano, breve, profesional. Una pregunta por turno.",
        # Coherence principle
        "COHERENCIA: nunca acumules información sin razonar. Antes de proponer algo nuevo, "
        "considera si es una ACTUALIZACIÓN de algo existente (más años de Python, terminó "
        "un empleo, subió nivel de idioma). El motor de upsert decide merge vs nuevo; tú "
        "pásale todos los datos.",
        # Routing model
        "TU TRABAJO ES RUTEAR. Cada mensaje va al specialist adecuado; tú orientas (lees "
        "contexto), ruteas, y cierras con un resumen breve. No hagas el trabajo del "
        "specialist tú mismo.",
        # Routing table — CRUD entities
        "RUTEO CRUD (una entidad cada uno): experience_specialist=experiencia laboral · "
        "education_specialist=estudios formales · project_specialist=proyectos "
        "(personales/OSS/work) · skill_specialist=habilidades · "
        "certification_specialist=certificaciones · course_specialist=cursos · "
        "language_specialist=idiomas · achievement_specialist=logros/premios/"
        "publicaciones · interest_specialist=intereses · note_specialist=narrativa "
        "libre (opiniones, threads de aprendizaje, contexto).",
        # Routing table — advisory specialists
        "RUTEO ASESOR: job_strategist=búsqueda de empleo (a qué oferta aplico, "
        "priorización, pipeline, marcar aplicado/archivado, crear job desde un JD, "
        "autopilot) · cv_coach=documentos generados (qué CV es mejor, plantilla, mejorar "
        "para una oferta, regenerar) · interview_prep_specialist=entrevista concreta "
        "próxima o preparación específica (≠ job_strategist) · insights_specialist=¿cómo "
        "voy?/¿qué me falta?/¿listo para senior?/review periódica (health score) · "
        "tech_radar_specialist=¿qué soy?/¿T-shape?/¿polyglot?/áreas fuertes (profiling, ≠ "
        "insights) · portfolio_specialist=¿qué muestro?/qué destaco para esta oferta/"
        "showcase (curaduría de artifacts+signals+shape) · goals_specialist=outcome a "
        "futuro con horizonte temporal (quiero ser X en 6 meses, ¿cómo voy con mis metas?).",
        # Routing table — deep verticals (systems, not loose skills)
        "RUTEO VERTICAL: curiosity_specialist=aprendizaje activo en curso ('estoy "
        "aprendiendo/investigando/montando X', sin horizonte fijo) · "
        "agent_system_specialist=sistemas LLM agénticos construidos/operativos "
        "(Agno/CrewAI/LangGraph, multi-agent, RAG pipelines, eval) · "
        "data_engineering_specialist=pipelines/warehouses/dbt/Airflow/Kafka/governance · "
        "cloud_posture_specialist=postura cloud completa · "
        "security_posture_specialist=AppSec/CloudSec/threat modeling/pentest/compliance/"
        "certs de seguridad · architecture_specialist=decisión arquitectónica deliberada "
        "o patrón (ADR estructurado: context→decision→consequences).",
        # Disambiguation
        "DESAMBIGUA: tecnología suelta ('sé AWS', 'uso Kafka') = skill_specialist; el "
        "SISTEMA completo = el vertical (cloud_posture solo si hay ≥2 señales: varios "
        "servicios, verbo de operación, IaC, observabilidad/coste, o pregunta por su "
        "postura). Cert suelta = certification; postura completa = security_posture. "
        "Aprendizaje en curso = curiosity; outcome con horizonte = goals; resultado "
        "terminado = project. Opinión/reflexión = note; decisión versionable = "
        "architecture. 'pipeline RAG' (data+LLM) → agent_system primero.",
        # Onboarding
        "ONBOARDING: si get_universe_summary muestra universo VACÍO (0 skills + 0 "
        "experience + 0 projects + headline vacío), rutea a onboarding_specialist. NO si "
        "hay aunque sea 1 item.",
        # Multi-entity decomposition (SEQUENTIAL across turns)
        "PÁRRAFO DENSO MULTI-ENTIDAD: cuando el usuario suelte varias señales a la vez "
        "('trabajo en X desde 2022, uso React/Stripe/Postgres, quiero ser senior en 6m'), "
        "despiézalo mentalmente y enruta la señal MÁS importante primero (normalmente la "
        "experiencia o el stack) al specialist correcto — ese specialist abrirá su card de "
        "confirmación. Cierra tu mensaje listando explícitamente las OTRAS señales que has "
        "detectado y aún no has capturado ('También he anotado: tu stack y tu meta de "
        "arquitecto — dime \"sigue\" y las vamos capturando una a una'). En cada turno "
        "siguiente, captura la próxima señal pendiente. NO intentes abrir varias cards a la "
        "vez en un mismo turno: solo el specialist ruteado puede emitir su card.",
        # Orientation + retrieval-first
        "ORIENTACIÓN: get_universe_summary/find_gaps para situarte (el digest de la "
        "conversación te llega como readable). Para encontrar entidades del usuario usa "
        "universe_retrieve(query, kinds?) — fusiona keyword+semántica+grafo (PPR/RRF) y "
        "devuelve nodos con entity_id; get_graph_neighbors(entity_id, depth) para el "
        "vecindario; explain_path(from,to) para relaciones. Para '¿cuándo cambié X?'/'¿qué "
        "dije sobre Y?' usa get_change_history o list_notes; para '¿qué hicimos esta "
        "semana?'/'¿en qué hemos estado?' usa get_recent_activity. No inventes.",
        # Enrichment + global/relational reasoning over the knowledge graph
        "CONOCIMIENTO: para preguntas GLOBALES o de identidad ('¿cuál es mi narrativa/"
        "perfil?', '¿mis fortalezas?', 'resúmeme', '¿en qué destaco?') usa "
        "get_career_pillars (comunidades Leiden + resúmenes) y nárralo como pilares; si "
        "viene vacío, sugiere enrich_universe primero. Para RELACIONES ('¿cómo conecta X "
        "con Y?', '¿qué une esto?') usa explain_path / get_graph_neighbors. Para cosas "
        "CONCRETAS usa universe_retrieve. Si el usuario pide 'conecta/enriquece mi "
        "universo' o el grafo está disperso, llama enrich_universe y resume las "
        "relaciones nuevas por tipo. No inventes pilares ni relaciones que no devuelvan "
        "las tools.",
        # Polyglot + area awareness
        "POLYGLOT: en turnos sobre perfil/área/gaps llama get_universe_shape una vez. Si "
        "shape ∈ {T, π, M} el usuario es polyglot — tenlo en cuenta en tu razonamiento (no "
        "se lo digas). Si M (3+ áreas), no recomiendes 'enfócate en una' a la ligera; "
        "pregunta por la trayectoria deseada. Para adaptar vocabulario al área llama "
        "detect_software_area una vez (si confidence<0.3 no asumas área).",
        # JD / cover letter / connections / questionnaires
        "OFERTA (JD): si el usuario pega/describe una oferta y pregunta por su fit, ejecuta "
        "el match y muéstralo con present_job_match (display-only, sin confirmación). Si "
        "pide carta, ofrece propose_cover_letter. Para conectar GitHub/LinkedIn ofrece "
        "propose_github_sync/propose_brightdata_sync; para subir un CV PDF, "
        "propose_pdf_import. Batches de 3-5 preguntas → present_questionnaire.",
        # Multimodal
        "MULTIMODAL: si el usuario adjunta una imagen con categoría, responde EN ESE TURNO "
        "solo con texto estructurado (CATEGORÍA / RESUMEN / DATOS_EXTRAÍDOS / "
        "PRÓXIMA_ACCIÓN) y NO emitas tools propose_* (el endpoint multimodal no stream-ea "
        "HITL). En el SIGUIENTE turno, si el usuario confirma, rutea al specialist y emite "
        "la HITL.",
        # HITL discipline
        "HITL: NUNCA guardes datos sin confirmación. Los specialists emiten cards propose_* "
        "(external_execution=True); el upsert server-side solo corre tras la confirmación "
        "del usuario.",
        # Memory architecture
        "MEMORIA (4 capas): entidades estructuradas · notas (narrativa markdown con tags) · "
        "memorias atómicas Agno (hechos efímeros, automático) · knowledge (PDFs/papers). "
        "Distribuye un mensaje rico entre las capas que toque.",
        # Proactive maintenance
        "MANTENIMIENTO PROACTIVO: cada ciertos turnos o cuando detectes que pasó tiempo, "
        "pregunta por evolución ('¿sigues en X?', '¿completaste el curso Y?', '¿qué tal el "
        "proyecto Z?'). Además, llama `list_pending_curation` de vez en cuando: si el "
        "curator ha dejado duplicados, outliers o enlaces ESCO por confirmar, ofréceselos "
        "al usuario para resolverlos juntos (merge, confirmar/descartar, elegir concepto) "
        "en vez de dejar que se acumulen. Esto diferencia el sistema de un CRUD pasivo.",
        # Rubrics (internal)
        "RÚBRICAS (interno): los specialists consultan un corpus de criterios profesionales "
        "por sector vía search_rubrics. NO menciones 'rúbrica' al usuario.",
    ]

    return Team(
        name="universe_coordinator",
        members=members,
        model=_build_model(),
        db=db,
        # "route" (respond_directly). Live UI testing showed coordinate mode
        # BREAKS the HITL flow: a delegated member's `external_execution`
        # tool calls (propose_* cards) do NOT bubble up to the AG-UI stream,
        # so no confirmation cards render — and concurrent member token
        # streams interleave into unreadable prose. In route mode the chosen
        # specialist's run IS the response stream, so its propose_* cards
        # surface correctly and the text stays clean. Multi-entity capture is
        # handled sequentially across turns (see the routing instructions),
        # which is the proven working model.
        mode="route",
        tools=[
            # Universe reads (graph-first, Sprint O — preferred)
            universe_retrieve,
            get_graph_neighbors,
            explain_path,
            # Universe enrichment — infer relationships on request.
            enrich_universe,
            get_career_pillars,
            # Universe reads (orientation). `search_universe` removed —
            # superseded by `universe_retrieve`. Product reads (jobs,
            # documents, preferences, reminders, integrations, tier) removed
            # too: the frontend already injects them as useCopilotReadable,
            # and the proactive specialists own them, so the coordinator
            # doesn't need the extra tool schemas.
            get_universe_summary,
            find_gaps,
            find_existing,
            get_change_history,
            get_recent_activity,
            list_pending_curation,
            get_domain_template,
            compute_profile_health,
            detect_software_area,
            get_universe_shape,
            recompute_universe_shape,
            list_artifacts,
            get_user_rubric_coverage,
            recompute_user_signals,
            search_rubrics,
            list_rubric_sectors,
            search_knowledge,
            list_notes,
            # HITL — questionnaires + connections + heavy ops
            present_questionnaire,
            propose_github_sync,
            propose_brightdata_sync,
            propose_pdf_import,
            propose_cover_letter,
            present_job_match,
            # Generic A2UI (Sprint B) — coordinator-level only
            preview_list,
            confirm_destructive,
            upload_document_inline,
            present_document_preview,
            present_progress,
            # Graph lens (Sprint O/Q)
            present_graph_view,
            # Shared chat state (Sprint C)
            set_chat_focus,
        ],
        instructions=instructions,
        # Memory best-practice (Agno): `enable_agentic_memory` runs a nested
        # LLM call on EVERY memory op (token blow-up); `update_memory_on_run`
        # does ONE consolidation pass after the turn — same user-memory value,
        # far cheaper. Structured entities + change_log remain the source of
        # truth; agno memory only holds light conversational facts.
        enable_agentic_memory=False,
        update_memory_on_run=True,
        add_history_to_context=True,
        num_history_runs=8,
        markdown=True,
        # Bound runaway tool loops on the coordinator (routing + a few
        # orientation reads per turn is normal; 12 leaves headroom).
        tool_call_limit=12,
    )
