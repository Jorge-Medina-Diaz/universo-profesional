# Agents architecture (Sprint 4)

## Vision

The system is not a CRUD with chat bolted on — it's a **reasoner with
intelligent persistence**. Every interaction goes through a coordinator
+ specialists team that understands intent, routes to the right specialist,
and mutates the user's universe via the **Coherence Engine** (not direct
writes). Data evolves over time; nothing accumulates blindly.

## Four memory layers

| Layer | Storage | Used for | Owner |
|---|---|---|---|
| **Universe entities** | `educations`, `experiences`, `skills`, … (9 tables) | Structured biography — what a CV needs | App |
| **Notes** | `notes` (markdown + tags) | Narrative biography: learning threads, opinions, ongoing projects | App |
| **Agno memories** | `agno_memories` | Atomic facts ("vegetariano", "remoto-only") gestionado automáticamente | Agno |
| **Knowledge** | `agno_knowledge_chunks` (PgVector) | Long documents (PDFs, papers) | Agno |

When the user says *"estas semanas he estado investigando RAG, leí 3 papers
e hice un demo con LlamaIndex"*, the coordinator distributes:

1. **Universe**: `upsert_project(demo)`, `upsert_skill(LlamaIndex, derived_from_project_id=demo)`, `upsert_skill(RAG)`, `upsert_interest(RAG)`.
2. **Notes**: `add_note(body="…", tags=["rag","papers","learning-thread-2026-may"])`.
3. **Memories**: Agno persists "actualmente investigando RAG (mayo 2026)" automatically.
4. **Knowledge**: when the user uploads the PDFs, `ingest_document` chunks them into PgVector (W4+ wiring).

## Coordinator + 10 specialists

```
universe_coordinator (Team, mode="route")
 ├─ experience_specialist     · upsert_experience  + propose_experience
 ├─ education_specialist      · upsert_education   + propose_education
 ├─ project_specialist        · upsert_project     + propose_project
 ├─ skill_specialist          · upsert_skill       + propose_skill + present_questionnaire + mark_stale
 ├─ certification_specialist  · upsert_certification + propose_certification
 ├─ course_specialist         · upsert_course      + propose_course
 ├─ language_specialist       · upsert_language    + propose_language
 ├─ achievement_specialist    · upsert_achievement + propose_achievement
 ├─ interest_specialist       · upsert_interest    + propose_interest
 └─ note_specialist           · add_note / update_note / list_notes  (narrative layer)

Coordinator-level tools shared across the whole team:
  get_universe_summary · find_gaps · search_universe · find_existing
  get_change_history · search_knowledge · list_notes
  present_questionnaire · propose_github_sync / brightdata / pdf_import
```

`mode="route"` means the coordinator's LLM picks the right specialist per
turn. Each specialist owns one entity but can also call coordinator-level
read tools when it needs context.

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

## Request flow

```
1. Frontend CopilotKit POSTs /agui with the JWT bearer.
2. agui_router validates JWT → derives user_id → overrides
   forwarded_props.user_id AND thread_id (always main-<user_id>).
3. run_team(coordinator, run_input) streams AG-UI events.
4. Coordinator routes to a specialist; specialist invokes propose_*
   (external_execution=True) → frontend renders an EntryCard.
5. User confirms → frontend POSTs /api/v1/coherence/upsert with the args.
6. UpsertUniverseEntity finds existing, merges or creates, records
   change_log, links evidence, returns UpsertOutcome.
7. Frontend renders DiffCard with the field-level diffs; agent receives
   the JSON back and acknowledges in chat ("merged: years 5→6").
```

## Files (Sprint 4 additions)

- `backend/src/coherence/{domain,application,infrastructure,interfaces}/`
- `backend/src/notes/{domain,application,infrastructure,interfaces}/`
- `backend/src/agents/specialists/note.py`
- `backend/src/agents/tools/{coherence_tools,knowledge_tools,notes_tools}.py`
- `backend/src/agents/workflows/{curator,session_digest}.py`
- `backend/src/agents/memory/sliding_window.py`
- `frontend/src/pages/{HomePage,NotesPage}.tsx`
- `frontend/src/chat/UniverseDrawer.tsx`
- `frontend/src/chat/cards/DiffCard.tsx`
- Alembic 0006/0007/0008.
