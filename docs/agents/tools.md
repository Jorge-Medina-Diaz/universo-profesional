# Agent tools catalogue

Tools live in `backend/src/agents/tools/`, split by flavour. Adding a new
tool follows the same pattern in every file — see the per-category sections.

## `ui_widgets.py` — generative UI cards

`@tool(external_execution=True)` declarations. The Python body never runs;
Agno emits the call as an AG-UI tool-call event the React layer renders.
**Tool names MUST match the `useCopilotAction({ name })` in
[`frontend/src/chat/actions/`](../../frontend/src/chat/actions/).**

| Name | Payload | Frontend card |
|---|---|---|
| `propose_experience` | org, role, start_date, end_date, is_current, description, highlights[], competences[] | `EntryCard` |
| `propose_education` | institution, degree, field_of_study, start_date, end_date, is_current, description, highlights[] | `EntryCard` |
| `propose_project` | name, description, role, project_type, tech_stack[], highlights[], impact, url, is_current | `EntryCard` |
| `propose_skill` | name, category, level, years, last_used_year | `EntryCard` |
| `propose_certification` | name, issuer, issued_on, expires_on, credential_id, verification_url | `EntryCard` |
| `propose_course` | title, platform, started_on, completed_on, duration_hours, certificate_url | `EntryCard` |
| `propose_language` | code (ISO-639-1), name, level (CEFR), certification | `EntryCard` |
| `propose_achievement` | title, achieved_on, description, context, evidence_url | `EntryCard` |
| `propose_interest` | name, description | `EntryCard` |
| `present_questionnaire` | title, intro, questions[], submit_label | `QuestionnaireCard` (single_choice/multi_choice/scale/open) |
| `propose_github_sync` | — | `EntryCard` confirm |
| `propose_brightdata_sync` | — | `EntryCard` confirm (PRO) |
| `propose_pdf_import` | — | `EntryCard` redirect to /connections |
| `propose_document_generation` | kind, template, tone, language, job_description | `EntryCard` confirm |
| `propose_cover_letter` | job_description, template, tone, language | `EntryCard` confirm |
| `propose_cv_regenerate` | document_id, overrides | `EntryCard` confirm |
| `propose_esco_disambiguation` | entity_id, candidates[] | `EscoDisambigCard` |
| `propose_edge_creation` | from_id, to_id, edge_type, metadata | `EntryCard` confirm |
| `propose_edge_deletion` | from_id, to_id, edge_type | `EntryCard` confirm |

### HITL proposal flow

All `propose_*` tools are `external_execution=True`.  The flow is:

1. **Agent emits** the tool call → CopilotKit serialises it as an AG-UI event.
2. **Frontend renders** the matching React card (`EntryCard`, `EscoDisambigCard`, etc.).
3. **User acts:**
   - *Confirm* → frontend `POST /api/v1/coherence/upsert` with the payload.
   - *Reject* → frontend calls `record_agent_feedback` with `sentiment="negative"`.
   - *Edit* → frontend patches the payload, then POSTs upsert + neutral/positive feedback.
4. **Backend upserts** via Coherence Engine → returns `UpsertOutcome` with field-level diffs.
5. **Frontend renders** `DiffCard` so the user sees what changed.
6. **Agent receives** the outcome JSON and acknowledges in chat ("Añadido: Docker (nivel avanzado)").

No data is persisted until step 3 (confirm).  This is the only write path for
user-facing chat interactions.

### Adding a new card

1. Add a `@tool(external_execution=True)` decorated function in
   `ui_widgets.py` with the desired argument schema.
2. Mirror the name and parameters in `useCopilotAction` inside
   `frontend/src/chat/actions/` using `renderAndWaitForResponse`.
3. (Optional) Compose a specialist that owns it via
   `src/agents/specialists/<entity>.py`.

## `universe_writes.py` — server-side persistence

Wrap existing `*Crud` use cases. Each opens a fresh `AsyncSession`, sets the
RLS user from `RunContext.user_id`, calls `crud.add(...)`, commits the UoW.
These tools are the persistence fallback path — the primary path remains the
universe REST API invoked from the confirmation card. They're useful when an
agent runs unattended (e.g., scheduled jobs) and has no UI.

Pattern (~10 lines per new entity):
```python
@tool(name="add_<entity>", description="...")
async def add_<entity>(run_context: RunContext, ...):
    return await _run_crud_add(
        user_id=run_context.user_id,
        payload=_strip_none(...),
        crud_class_name="<Entity>Crud",
        repo_class_name="SqlAlchemy<Entity>Repository",
    )
```

## `universe_reads.py` — what the agent can inspect

| Name | Returns |
|---|---|
| `get_universe_summary` | Counts per entity + headline + top skills + recent experiences + languages |
| `find_gaps` | List of suggestions from the rule engine (`MissingSkillProvider`, `StaleSkillProvider`, etc.) |
| `search_universe` | Semantic search hits across the user's entities |

## `discovery_tools.py` — conversational profile building

| Name | Returns | When to use |
|---|---|---|
| `get_profile_completeness` | Counts + coverage % per dimension + sparse list | Agent wants to know what's missing before asking |
| `suggest_discovery_questions` | Targeted questions + rationale + expected entities | Agent needs natural questions to fill gaps |

These tools power the **`discover_profile`** intent.  Instead of formal quizzes
or exams, the agent asks *conversational* questions grounded in the actual
profile gaps: "¿Has tenido algún proyecto personal del que estés orgulloso?",
"¿En qué crees que podrías aportar valor sin dudarlo?".  Every answer flows
through the `UniverseEnrichmentEngine` and materialises in the graph.

## `document_tools.py` — document generation support

| Name | Returns | When to use |
|---|---|---|
| `list_document_templates` | Array of template metadata (name, kind, description, best_for, language_support) | Recommending a template conversationally |
| `get_document_template` | Single template detail | User asks about a specific template |
| `get_document` | Document metadata + content summary (experience_count, skill_count, etc.) | Referring to an existing CV or cover letter |

These tools let the `document_specialist` discover what the user already has
before proposing new generation.  They prevent the agent from exhausting the
LLM context window with full document contents.

## `graph_query_tools.py` — natural language graph queries

| Name | Returns | When to use |
|---|---|---|
| `query_graph` | Executed Cypher + rows + explanation | Complex graph questions: "¿qué skills usa mi proyecto más reciente?" |
| `explain_graph_query` | Cypher string + params (no execution) | Debugging or showing the user the translation |

Both delegate to `Text2CypherEngine` which generates openCypher from natural
language, validates it, executes it on Apache AGE, and returns structured
results.

## `learning_tools.py` — self-learning feedback loop

| Name | Returns | When to use |
|---|---|---|
| `record_agent_feedback` | `{ "status": "recorded" }` | After any HITL rejection, heavy edit, or enthusiastic confirmation |

Captures:
- `trigger_message` — what the user said that caused the action.
- `agent_action` — what the agent did (e.g. `proposed_skill: Docker`).
- `user_expectation` — what the user wanted instead.
- `sentiment` — `positive` | `negative` | `neutral`.

The `SelfLearningEngine` stores this in `user_procedural_memory`.  A periodic
`consolidate` workflow groups similar examples into active rules that the
Context Providers inject into agent instructions.  No fine-tuning, no GPU —
pure context engineering.

## `universe_enrichment.py` — auto-materialisation engine

`UniverseEnrichmentEngine` runs **after every chat turn** (fire-and-forget) to:

1. **Extract entities** from free text via LLM (skills, experiences, projects, etc.)
2. **Extract relations** between them ("used Python in project X")
3. **Resolve duplicates** via Entity Resolution v2
4. **Upsert nodes + edges** into AGE
5. **Link to ESCO** where possible

This is how the graph grows *organically* — the user never has to say "add this
skill"; they just describe their work and the system materialises the knowledge.

## `memory.py` (planned)

Thin helpers for `agent.add_user_memory(...)` and `agent.get_user_memories(...)`.
Most of the time `enable_agentic_memory=True` covers it — these helpers are
for cases where you want a specialist to be explicit about what to remember
(e.g., "store_user_preference('avoid public speaking')").

## How specialists pick their tools

`build_specialist(...)` accepts a `tools=[...]` list. Each specialist gets:
- Its own `propose_*` (the only writer in HITL paths).
- Its matching `add_*` (server-side fallback).
- Optionally `present_questionnaire` for batch capture (used by
  `skill_specialist`).

The coordinator additionally owns the **reads** and the **import proposals**
(github/brightdata/pdf), so any specialist can defer to "let's import that
instead" without each one duplicating the wiring.
