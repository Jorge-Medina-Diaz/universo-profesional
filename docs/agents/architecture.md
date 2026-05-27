# Agents architecture (Sprint R)

## Vision

The system is not a CRUD with chat bolted on — it's a **reasoner with
intelligent persistence**. Every interaction goes through a coordinator
+ specialists team that understands intent, routes to the right specialist,
and mutates the user's universe via the **Coherence Engine** (not direct
writes). Data evolves over time; nothing accumulates blindly.

## Four memory layers

| Layer | Storage | Used for | Owner |
|---|---|---|---|
| **Universe entities** | `educations`, `experiences`, `skills`, … (11 graph labels) | Structured biography — what a CV needs | App |
| **Graph** | Apache AGE (`universe_personal`) | Typed entities + relations (trajectory, gaps, ESCO links) | App |
| **Notes** | `notes` (markdown + tags) | Narrative biography: learning threads, opinions, ongoing projects | App |
| **Agno memories** | `agno_memories` | Atomic facts ("vegetariano", "remoto-only") gestionado automáticamente | Agno |
| **Knowledge** | `agno_knowledge_chunks` (PgVector) | Long documents (PDFs, papers) | Agno |
| **Structured memory** | `user_semantic_memory`, `user_procedural_memory`, `session_episodes` | Self-learning context (facts, rules, episodes) | App |

When the user says *"estas semanas he estado investigando RAG, leí 3 papers
e hice un demo con LlamaIndex"*, the coordinator distributes:

1. **Universe**: `upsert_project(demo)`, `upsert_skill(LlamaIndex, derived_from_project_id=demo)`, `upsert_skill(RAG)`, `upsert_interest(RAG)`.
2. **Notes**: `add_note(body="…", tags=["rag","papers","learning-thread-2026-may"])`.
3. **Memories**: Agno persists "actualmente investigando RAG (mayo 2026)" automatically.
4. **Knowledge**: when the user uploads the PDFs, `ingest_document` chunks them into PgVector (W4+ wiring).

## Coordinator + 28 specialists (MVP)

The team keeps 28 specialists for the MVP (refactor to 4 meta-agents deferred).
Each specialist owns one domain and exposes `propose_*` HITL tools where
applicable.

```
universe_coordinator (Team, respond_directly=True)
 ├─ experience_specialist       · upsert_experience  + propose_experience
 ├─ education_specialist        · upsert_education   + propose_education
 ├─ project_specialist          · upsert_project     + propose_project
 ├─ skill_specialist            · upsert_skill       + propose_skill + mark_stale
 ├─ certification_specialist    · upsert_certification + propose_certification
 ├─ course_specialist           · upsert_course      + propose_course
 ├─ language_specialist         · upsert_language    + propose_language
 ├─ achievement_specialist      · upsert_achievement + propose_achievement
 ├─ interest_specialist         · upsert_interest    + propose_interest
 ├─ note_specialist             · add_note / update_note / list_notes
 │
 ├─ discover_profile_specialist · get_profile_completeness + suggest_discovery_questions
 ├─ document_specialist         · list_document_templates + propose_document_generation
 │                                (conversational discovery before generation)
 ├─ cv_coach                    · document coaching, template advice, regeneration
 ├─ onboarding_specialist       · batch ingest (CV, LinkedIn, dictado en bloque)
 ├─ job_strategist              · job matching, application strategy
 ├─ portfolio_specialist        · artifact curation, showcase
 ├─ curiosity_specialist        · active learning threads (no fixed horizon)
 ├─ goals_specialist            · outcome goals with temporal horizon
 ├─ insights_specialist         · health score, gap analysis, readiness review
 ├─ interview_prep_specialist   · interview simulation, Q&A prep
 ├─ tech_radar_specialist       · T-shape / polyglot profiling
 ├─ agent_system_specialist     · LLM agent systems (RAG, multi-agent, eval)
 ├─ data_engineering_specialist · pipelines, warehouses, governance
 ├─ cloud_posture_specialist    · cloud infrastructure posture
 ├─ security_posture_specialist · AppSec, CloudSec, compliance
 ├─ architecture_specialist     · ADR-style architectural decisions
 └─ (career/social providers exist but are deprioritised)

Coordinator-level tools:
  get_universe_summary · find_gaps · search_universe · find_existing
  get_change_history · search_knowledge · list_notes
  query_graph · explain_graph_query
  get_profile_completeness · suggest_discovery_questions
  propose_github_sync / brightdata / pdf_import
```

`respond_directly=True` with `determine_input_for_members=False` means the
coordinator's LLM picks the right specialist per turn and the specialist
replies directly (no team-level re-synthesis). Each specialist owns one
domain but can also call coordinator-level read tools when it needs context.

## Coherence Engine

All writes route through `backend/src/coherence/`. Flow:

1. **Find existing.** Exact match on the canonical name field
   (case-insensitive). If miss, semantic match via `PgVectorSemanticMatcher`
   (cosine ≥ 0.92 → auto-merge; ≥ 0.80 and < 0.92 → ambiguous → emit
   suggestion; < 0.80 → not a match).
2. **Merge or create.** No match → call the existing `*Crud.add`. Match →
   apply per-entity `MergePlan` from `merge_rules.py` and write via
   `*Crud.update`.
3. **Record change.** One row per field changed in `universe_change_log`
   (append-only).
4. **Auto-evidence.** Skill upserts with `derived_from_*_id` fields create
   `evidences` rows automatically — the universe becomes a graph.

See [coherence-engine.md](./coherence-engine.md) for merge rules per entity
and [data-evolution.md](../architecture/data-evolution.md) for the change_log
schema and trajectory queries.

## Single chat

Every user has exactly one persistent chat session. The AGUI router enforces
`thread_id = main-<user_id>` on every request, ignoring whatever the client
sent. Long-term context survives across browser sessions and devices.

To keep the LLM prompt bounded, a daily `session_digest` workflow compacts
messages older than `WINDOW_SIZE = 40` into a structured digest
(`{open_questions, decisions, mentioned_entities, mentioned_topics}`) stored
in `chat_session_meta.metadata.digest` and injected as a CopilotKit
readable on every turn.

See [single-chat.md](./single-chat.md) for the sliding window mechanics.

## Curator workflow

`backend/src/agents/workflows/curator.py` runs daily at 03:00 UTC (arq cron).
For each user active in the last 30 days:

- Detects duplicates via embedding cosine ≥ 0.94. Opens a
  `kind="merge_candidates"` suggestion (never auto-merges — user confirms).
- Cleans orphan `evidences` rows (target entity deleted).
- Decays `confidence` for entries unreviewed in > 365 days (`× 0.9`, floor 0.3).

The output is just `suggestions` rows; nothing user-facing changes without
confirmation. The user reviews them in the chat or in the Universe drawer's
"Sugerencias" tab.

## Conversational discovery pattern

The `discover_profile` intent replaces quizzes and forms with natural dialogue.
The pattern is **context → capture → enrich**:

1. **Context.** The specialist calls `get_profile_completeness` to see which
dimensions are sparse (e.g. `project` and `certification` below 50 %).
2. **Capture.** It calls `suggest_discovery_questions` to obtain 1-3
personalised, conversational questions grounded in what the user already has:
"Veo que tienes experiencia en backend. ¿Has liderado algún proyecto técnico?"
Only one question per turn.
3. **Enrich.** The user's answer flows through `UniverseEnrichmentEngine`
(fire-and-forget) which extracts implicit entities and relations and
materialises them in AGE automatically. The graph grows without explicit commands.

This loop repeats until coverage improves or the user signals they are done.

## Request flow

```
1. Frontend CopilotKit POSTs /agui with the JWT bearer.
2. agui_router validates JWT → derives user_id → overrides
   forwarded_props.user_id AND thread_id (always main-<user_id>).
3. Intent Router classifies message → injects provider memory context.
4. run_team(coordinator, run_input) streams AG-UI events.
5. Coordinator routes to a specialist; specialist invokes propose_*
   (external_execution=True) → frontend renders an EntryCard.
6. User confirms → frontend POSTs /api/v1/coherence/upsert with the args.
7. UpsertUniverseEntity finds existing, merges or creates, records
   change_log, links evidence, returns UpsertOutcome.
8. Frontend renders DiffCard with the field-level diffs; agent receives
   the JSON back and acknowledges in chat ("merged: years 5→6").
9. Post-run (fire-and-forget): UniverseEnrichmentEngine processes the
   raw user message → extracts implicit entities/relations → materialises
   them in AGE automatically. The graph grows even when the user never
   clicks "confirm".
10. If user rejects/edits, record_agent_feedback stores the correction
    in user_procedural_memory for the self-learning loop.
```

## Intents (Universo Profesional focus)

| Intent | Provider | Description |
|---|---|---|
| `expand_universe` | `universe_curator` | Add/update experiences, skills, projects, etc. |
| `generate_document` | `document_specialist` | CV, cover letter, portfolio — with conversational discovery first |
| `discover_profile` | `discover_profile_specialist` | Natural questions to reveal hidden gaps |
| `explore_graph` | `universe_curator` | Traverse graph: trajectory, gaps, related skills |
| `general_chat` | `universe_curator` | Greeting, small talk, meta questions |

> **Removed**: `quiz_skills` — we don't do exams/quizzes. Conversational
discovery via `discover_profile` replaces formal assessment.

## Files (Sprint R additions)

- `backend/src/agents/context_providers/{base,router,universe_provider,document_provider}.py`
- `backend/src/agents/workflows/universe_enrichment.py`
- `backend/src/agents/tools/{discovery_tools,document_tools,graph_query_tools,learning_tools}.py`
- `backend/src/agents/memory/{structured_memory,self_learning}.py`
- `backend/src/graph/application/{text2cypher,universe_graph,cross_encoder}.py`
- `backend/src/graph/domain/{esco_types,custom_skills_ontology}.py`
- `backend/src/coherence/application/entity_resolution.py`
- `backend/src/coherence/domain/er_rules.py`
- Alembic 0023 (typed graph labels) / 0024 (agent architecture v2).
