"""Build the Agno team that drives chat-first universe capture.

The factory is the single composition root for agents: pick the LLM provider,
load the 9 specialists (one per universe entity) + a routing coordinator,
expose the result. We build the team once (lru_cache) and reuse it for every
request — Agno's `Team` is stateless (state lives in the configured DB), so
concurrent requests are safe.
"""
from __future__ import annotations

from contextvars import ContextVar
from functools import lru_cache
from typing import Literal

from agno.models.base import Model

from src.shared.config import get_settings
from src.shared.db import get_engine

ModelTier = Literal["coordinator", "specialist"]

# BYOK override: when set (to (provider, api_key)) for the duration of a team
# build, `_build_model` uses the user's own key + provider instead of the
# platform key. The global cached team is always built with this UNSET, so the
# default (platform-key) path is byte-for-byte unchanged.
_byok_override: ContextVar[tuple[str, str] | None] = ContextVar(
    "_byok_override", default=None
)

# Output cap per run. Routing + most card-emitting turns are short; this
# bounds runaway generation cost without truncating normal replies.
_MAX_TOKENS = 4096
# Low (but non-zero — Agno treats 0.0 as "unset") temperature for the
# coordinator so routing is near-deterministic; specialists get a touch
# more room for natural phrasing.
_TEMPERATURE_BY_TIER: dict[str, float] = {"coordinator": 0.1, "specialist": 0.3}

# Static coordinator instructions — these rarely change and are prime candidates
# for Anthropic prompt caching (see system_prompt_blocks in _build_model).
STATIC_INSTRUCTIONS = [
    # Identity + tone
    "Eres el compañero agéntico que entiende, estructura y MANTIENE el universo "
    "profesional del usuario — un grafo de conocimiento vivo, no un formulario. "
    "Idioma por defecto: español (cambia si lo piden). Tono cercano, breve, profesional. "
    "Una pregunta por turno. NUNCA hagas exámenes, tests ni cuestionarios formales. "
    "Descubre el perfil mediante diálogo natural: 'cuéntame sobre…', '¿cómo fue…?', "
    "'¿qué usaste en…?'.",
    # The graph is the source of truth
    "EL GRAFO ES LO PRIMERO: el universo del usuario vive en un grafo (Apache AGE). "
    "Cada entidad es un nodo; las relaciones son edges (USES_TECH, PART_OF, DERIVED_FROM, "
    "EVIDENCES_SIGNAL). Cuando hables de su perfil, piensa en conexiones, no en listas. "
    "Usa get_graph_neighbors, explain_path y query_graph para explorar. El SQL es solo "
    "persistencia; el grafo es la narrativa.",
    # Auto-enrichment: the system extracts automatically
    "AUTO-ENRICHMENT: después de cada turno, un motor extrae automáticamente entidades "
    "y relaciones del texto del usuario y las materializa en el grafo. TÚ NO necesitas "
    "forzar la extracción en cada frase. Tu trabajo es CONVERSAR, indagar, contextualizar. "
    "Si el usuario dice 'usé Python en mi proyecto X', el sistema ya creará el skill y "
    "la relación. Tú sigue la conversación: '¿qué más usaste?', '¿cuánto duró el proyecto?'.",
    # Coherence principle
    "COHERENCIA: nunca acumules información sin razonar. Antes de proponer algo nuevo, "
    "considera si es una ACTUALIZACIÓN de algo existente (más años de Python, terminó "
    "un empleo, subió nivel de idioma). El motor de upsert decide merge vs nuevo; tú "
    "pásale todos los datos.",
    # Conversational discovery (replaces quizzes/exams)
    "DESCUBRIMIENTO CONVERSACIONAL: cuando el perfil esté vacío o disperso, NO lances "
    "un cuestionario masivo. Usa get_profile_completeness para ver qué dimensiones faltan, "
    "luego suggest_discovery_questions para obtener preguntas naturales y contextualizadas. "
    "Haz UNA pregunta por turno, conectando con lo que el usuario ya dijo. Ejemplo: "
    "'Veo que tienes experiencia en backend. ¿Has liderado algún proyecto técnico?' → "
    "esto descubre skill 'Liderazgo técnico' + project. Otro: '¿Qué herramienta usas "
    "para tests?' → skill 'Testing'. Las respuestas se enriquecen automáticamente.",
    # Routing model
    "TU TRABAJO ES RUTEAR. Cada mensaje va al specialist adecuado; tú orientas (lees "
    "contexto), ruteas, y cierras con un resumen breve. No hagas el trabajo del "
    "specialist tú mismo. Rutea a UN SOLO specialist por turno — NUNCA delegues a "
    "varios 'en paralelo' ni en el mismo turno (sus respuestas se entremezclan en un "
    "texto ilegible y rompen las cards). Si hay varias entidades, eso es una INGESTA "
    "(ver abajo): va entera a onboarding_specialist, no repartida.",
    # Intent awareness (injected by router)
    "INTENT ROUTING: el mensaje del usuario ya fue clasificado antes de llegarte. "
    "El intent está en session_state['_provider_intent']: expand_universe (añadir/actualizar), "
    "discover_profile (preguntar para revelar gaps), explore_graph (navegar trayectoria), "
    "generate_document (CV/carta), general_chat (saludo/small-talk). Respeta el intent: "
    "si es discover_profile, NO propongas añadir entidades directamente; haz preguntas. "
    "Si es explore_graph, usa query_graph o explain_path para mostrar conexiones.",
    # Routing table — CRUD entities
    "RUTEO CRUD (una entidad cada uno): experience_specialist=experiencia laboral · "
    "education_specialist=estudios formales · project_specialist=proyectos "
    "(personales/OSS/work) · skill_specialist=habilidades · "
    "certification_specialist=certificaciones · course_specialist=cursos · "
    "language_specialist=idiomas · achievement_specialist=logros/premios/"
    "publicaciones · interest_specialist=intereses · note_specialist=narrativa "
    "libre (opiniones, threads de aprendizaje, contexto).",
    # Routing table — advisory specialists
    "RUTEO ASESOR: discover_profile_specialist=descubrir el perfil mediante diálogo "
    "natural (NO exámenes) · cv_coach=documentos generados (qué CV es mejor, plantilla, "
    "mejorar para una oferta, regenerar) · interview_prep_specialist=entrevista concreta "
    "próxima o preparación específica · insights_specialist=¿cómo "
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
    # Multi-entity decomposition — EN LOTE, no 1 a 1
    "PÁRRAFO DENSO MULTI-ENTIDAD: cuando el usuario suelte VARIAS entidades a la vez "
    "('trabajé en X desde 2022, uso React/Stripe/Postgres, hice un proyecto Y'), NO lo "
    "captures señal a señal en turnos sucesivos. RUTEA a onboarding_specialist para que "
    "abra UNA `present_import_review` con todo el lote (mismo flujo que INGESTA). Las "
    "intenciones que NO son entidades del universo (crear una meta, cambiar "
    "preferencias) sí van con su card propia (propose_goal / propose_preferences_update) "
    "en turnos aparte.",
    # Orientation + retrieval-first
    "ORIENTACIÓN: get_universe_summary/find_gaps para situarte. Para encontrar entidades "
    "usa universe_retrieve(query, kinds?) — keyword+semántica+grafo (PPR/RRF). "
    "get_graph_neighbors(entity_id, depth) para el vecindario; explain_path(from,to) "
    "para relaciones. query_graph(pregunta_en_natural) para consultas complejas al grafo "
    "('¿qué skills usa mi proyecto más reciente?'). Para '¿cuándo cambié X?' usa "
    "get_change_history. No inventes.",
    # Capture rubric — minimal relevant fields per kind
    "RÚBRICA DE CAPTURA (mínimos por entidad): experiencia = empresa + puesto + lugar + "
    "fechas; skill = nombre + nivel + años; education = institución + título + campo + "
    "fechas; project = nombre + rol + stack; certification = nombre + emisor + fecha; "
    "course = título + plataforma + fecha; language = idioma + nivel. Si falta un mínimo, "
    "PREGÚNTALO — no guardes a medias. Usa find_incomplete_entities para ver qué está incompleto.",
    # References / evidence — back claims with sources
    "REFERENCIAS/EVIDENCIA: cuando algo se aprendió o se respalda con una fuente, ENLÁZALO: "
    "un libro/paper es un artifact; para respaldar skill/experiencia pasa derived_from_*_id "
    "al upsert → se materializa como evidencia en el grafo. Así un skill cita su origen.",
    # Graph reasoning
    "RAZONAMIENTO DE GRAFO: para preguntas globales ('¿cuál es mi narrativa?', '¿mis "
    "fortalezas?') usa get_career_pillars (comunidades Leiden). Para RELACIONES ('¿cómo "
    "conecta X con Y?') usa explain_path / get_graph_neighbors. Para cosas CONCRETAS "
    "usa universe_retrieve. Si pide 'enriquece mi universo' o el grafo está disperso, "
    "llama enrich_universe. No inventes.",
    # Polyglot + area awareness
    "POLYGLOT: en turnos sobre perfil/área/gaps llama get_universe_shape una vez. Si "
    "shape ∈ {T, π, M} el usuario es polyglot — tenlo en cuenta (no se lo digas). "
    "Si M (3+ áreas), no recomiendes 'enfócate en una' a la ligera; pregunta por la "
    "trayectoria deseada. detect_software_area para adaptar vocabulario (confidence<0.3 "
    "no asumas área).",
    # Document generation
    "DOCUMENTOS: si pide CV/carta/portfolio, rutea a document_specialist. "
    "Él hace descubrimiento conversacional y luego abre el generador. "
    "cv_coach sigue disponible para coaching de impacto y revisión de CV existentes. "
    "Para subir un CV PDF → propose_pdf_import.",
    # Ingesta confiable (CV/LinkedIn/dictado en bloque) — RUTEA al specialist
    "INGESTA (CONFIABLE, EN LOTE) — REGLA DURA: si el mensaje trae 2+ entidades "
    "capturables O dice 'mi CV / importa / añade esto', enruta a onboarding_specialist. "
    "Él extrae TODO y abre UNA `present_import_review`. PROHIBIDO: (a) lanzar varios "
    "specialists 'en paralelo'; (b) capturarlo tú; (c) emitir propose_* por entidad; "
    "(d) upsert directo sin card. Una ingesta = un route = una card. Tras confirmar, "
    "pasa a ENRIQUECIMIENTO; nunca re-propongas lo ya importado.",
    # Multimodal (imágenes sueltas, no CV)
    "MULTIMODAL: el adjunto va al modelo en el MISMO run. Si es CV/PDF de perfil o "
    "varias entidades → INGESTA → onboarding_specialist. Si es imagen suelta de UNA "
    "entidad concreta (diploma, certificado), rutea al specialist de esa entidad.",
    # HITL discipline
    "HITL: una mención conversacional de UNA entidad → su specialist abre propose_* "
    "(confirmación rápida). VARIAS entidades o ingesta → onboarding_specialist con "
    "present_import_review (revisión del conjunto, nunca 1 a 1). El upsert server-side "
    "solo corre tras la acción del usuario.",
    # Enrichment after capture
    "ENRIQUECIMIENTO TRAS CAPTURA: después de una ingesta, NO te quedes solo con lo dado. "
    "detect_software_area + get_universe_shape + find_gaps + search_rubrics(sector). "
    "Luego lanza UNA present_questionnaire (3-5 preguntas) sobre lo relevante que falta, "
    "conectando con lo que ya tiene ('veo que…'). Natural, no interrogatorio. Una tanda, "
    "ofrece seguir.",
    # Memory architecture
    "MEMORIA (4 capas): entidades estructuradas · notas (narrativa markdown con tags) · "
    "memorias atómicas Agno (hechos efímeros, automático) · knowledge (PDFs/papers). "
    "Distribuye un mensaje rico entre las capas que toque.",
    # Proactive maintenance
    "MANTENIMIENTO PROACTIVO: cada ciertos turnos pregunta por evolución ('¿sigues en X?', "
    "'¿completaste el curso Y?'). Llama list_pending_curation de vez en cuanto: si hay "
    "duplicados, outliers o enlaces ESCO por confirmar, ofréceselos al usuario. Esto "
    "diferencia el sistema de un CRUD pasivo.",
    # Self-learning feedback
    "APRENDIZAJE: si un usuario rechaza una propuesta (propose_*), llama record_feedback "
    "con el contexto para que el sistema aprenda. Ejemplo: rechazó 'Docker' como skill → "
    "feedback negativo con trigger='propuso Docker' para no repetir el error.",
    # Rubrics (internal)
    "RÚBRICAS (interno): los specialists consultan criterios profesionales por sector vía "
    "search_rubrics. NO menciones 'rúbrica' al usuario.",
]


def _build_model(tier: ModelTier = "coordinator") -> Model:
    """Pick a model instance for the given tier.

    Model tiering (the whole point of having a coordinator + cheap
    specialists): the coordinator routes and reasons → strong model
    (`agents_coordinator_model`, e.g. Sonnet); the 25 specialists work on
    small, focused payloads → cheap/fast model (`agents_specialist_model`,
    e.g. Haiku). Both fall back to a shim mock when no API key is
    configured so dev/test boot even offline.

    TODO(2026-06): Multi-provider fallback Anthropic → OpenAI on rate-limit.
    Implementing this cleanly requires a custom Model subclass that delegates
    to primary/secondary on `aresponse` / `aresponse_stream`. That touches
    Agno's internal streaming protocol (RunEvents, tool-call pauses, etc.) and
    is too risky for a single PR.  For now we rely on Team-level retries
    (`retries`, `exponential_backoff`) which re-try the *same* model.
    """
    settings = get_settings()
    # R5: opt-in deterministic scripted model for offline agent-loop tests.
    # The contextvar is None unless a test wraps the run in `scripted_model(...)`,
    # so this never backs a real user's agent.
    from src.agents.infrastructure.fake_llm import (
        FakeScriptedModel,
        get_scripted_steps,
    )

    _scripted = get_scripted_steps()
    if _scripted is not None:
        return FakeScriptedModel(_scripted)
    override = _byok_override.get()
    if override is not None:
        provider, byok_key = override
    else:
        provider = settings.agents_provider_resolved
        byok_key = None
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
        #
        # Verified (R14): the cached prefix is genuinely stable, so this IS a real
        # breakpoint. STATIC_INSTRUCTIONS is fully static and per-turn dynamic state
        # never enters the cached system block — Agno Team `add_session_state_to_context`
        # defaults False and we don't enable it, so `_provider_intent` lives in the
        # messages, not the prefix. Migrating to `system_prompt_blocks` only pays off
        # once a per-turn dynamic *suffix* is introduced; not needed today.
        return Claude(
            id=model_id,
            api_key=byok_key or settings.anthropic_api_key,
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
            api_key=byok_key or settings.openai_api_key,
            temperature=_TEMPERATURE_BY_TIER[tier],
            max_tokens=_MAX_TOKENS,
        )
    # Mock: OpenAI-compatible client pointed at an unreachable URL. Refuse
    # outright where mock isn't allowed (prod without a key) so we never serve
    # fabricated content as if real; otherwise actual LLM calls fail loudly,
    # signalling the user to configure ANTHROPIC_API_KEY or OPENAI_API_KEY.
    settings.assert_llm_usable()
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


def _build_universe_team():  # type: ignore[no-untyped-def]
    """Construct the universe coordinator team (uncached builder).

    Reads `_byok_override` (via `_build_model`) at build time, so building this
    while the contextvar is set yields a team wired to a user's BYOK key.
    """
    from agno.guardrails import PromptInjectionGuardrail
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
    from src.agents.specialists.discover_profile import build_discover_profile_specialist
    from src.agents.specialists.document_specialist import build_document_specialist
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

    # Sprint O — hybrid graph retrieval (BM25 + dense + PPR + RRF).
    from src.agents.tools.retrieval_tools import (
        enrich_universe,
        explain_path,
        get_career_pillars,
        get_graph_neighbors,
        universe_retrieve,
    )
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
        animate_graph,
        confirm_destructive,
        control_graph,
        present_document_preview,
        present_experience_card,
        present_graph_view,
        present_job_match,
        present_progress,
        present_project_card,
        present_questionnaire,
        present_skill_gap,
        present_trajectory,
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
        find_incomplete_entities,
        get_universe_summary,
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
        # Discovery specialist (Sprint R)
        build_discover_profile_specialist(db=db),
        # 2 proactive specialists (Sprint B)
        build_job_strategist(db=db),
        build_cv_coach(db=db),
        # Document generation specialist (conversational discovery)
        build_document_specialist(db=db),
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

    # R13 (experimental, default OFF): add ONE generalist that captures any
    # universe entity via the generic `propose_entity` tool, ALONGSIDE the
    # per-entity specialists above. Gated so the consolidated routing surface
    # can be A/B'd before the per-entity specialists are removed.
    if get_settings().agents_entity_curator_enabled:
        from src.agents.specialists.entity_curator import build_entity_curator

        members.append(build_entity_curator(db=db))

    return Team(
        name="universe_coordinator",
        members=members,
        model=_build_model(),
        db=db,
        # v2.6.9 route-mode flags — replaces deprecated `mode="route"`.
        # respond_directly=True  → the chosen member's run IS the response stream
        #                          (HITL cards surface correctly, text stays clean).
        # determine_input_for_members=False → coordinator decides routing itself.
        # share_member_interactions=True → members see each other's work.
        # add_team_history_to_members=True → members get team-level context.
        respond_directly=True,
        determine_input_for_members=False,
        share_member_interactions=True,
        add_team_history_to_members=True,
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
            find_incomplete_entities,
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
            # Graph lens (Sprint O/Q) + agent-driven graph control/animation
            present_graph_view,
            control_graph,
            animate_graph,
            # Rich generative insight cards
            present_trajectory,
            present_experience_card,
            present_project_card,
            present_skill_gap,
            # Shared chat state (Sprint C)
            set_chat_focus,
        ],
        instructions=STATIC_INSTRUCTIONS,
        # v2.6.9 native memory — session summaries + user memories.
        # These coexist with the app-level sliding_window digest (backend/src/agents/memory/)
        # which folds OLD messages into a structured summary.  Agno's native layer
        # handles light conversational facts; the sliding window handles long-horizon
        # compression.
        # TODO(2026-06): Deprecate sliding_window once Agno's native summaries alone
        # keep the context window bounded.
        enable_session_summaries=True,
        enable_user_memories=True,
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
        # Guardrails — run before every coordinator turn.
        # Team supports pre_hooks in v2.6.9; if it didn't we would apply them
        # to the coordinator Agent individually.
        pre_hooks=[
            PromptInjectionGuardrail(),
        ],
        # Team-level retries (same-model).
        # TODO(2026-06): Multi-provider fallback (see _build_model docstring).
        retries=2,
        delay_between_retries=2,
        exponential_backoff=True,
        # Bound runaway tool loops on the coordinator (routing + a few
        # orientation reads per turn is normal; 12 leaves headroom).
        tool_call_limit=12,
    )


@lru_cache(maxsize=1)
def get_universe_team():  # type: ignore[no-untyped-def]
    """The cached coordinator team built with the platform LLM key.

    This is the hot path for every non-BYOK user — a single shared, stateless
    team (state lives in the DB).
    """
    return _build_universe_team()


@lru_cache(maxsize=32)
def _byok_team(user_id: str, provider: str, key: str):  # type: ignore[no-untyped-def]
    """A coordinator team wired to one user's BYOK key.

    Cached by (user_id, provider, key) so a key rotation rebuilds. The Model
    objects capture the key at construction, so the cached team is safe to
    reuse after the contextvar is reset.

    Note (accepted): this reuses the platform team builder, so the session-summary
    / user-memory consolidation passes (enable_session_summaries,
    update_memory_on_run) also run on the user's key — i.e. a BYOK user's quota
    covers those background passes too, not only their visible turns. Acceptable
    for "runs on your account"; revisit if users expect turn-only billing.
    """
    token = _byok_override.set((provider, key))
    try:
        return _build_universe_team()
    finally:
        _byok_override.reset(token)


async def build_team_for_user(user_id: str):  # type: ignore[no-untyped-def]
    """Return the team to drive a run for `user_id`.

    Non-BYOK users get the exact same cached object as before; only users who
    configured their own key hit the (separately cached) per-user team. Any
    failure to resolve the key falls back to the platform team rather than
    breaking the chat.
    """
    try:
        from src.agents.infrastructure.byok import resolve_user_llm_credential

        cred = await resolve_user_llm_credential(user_id)
    except Exception:
        cred = None
    if not cred:
        return get_universe_team()
    provider, key = cred
    return _byok_team(user_id, provider, key)
