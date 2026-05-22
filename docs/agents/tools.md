# Agent tools catalogue

Tools live in `backend/src/agents/tools/`, split by flavour. Adding a new
tool follows the same pattern in every file — see the per-category sections.

## `ui_widgets.py` — generative UI cards

`@tool(external_execution=True)` declarations. The Python body never runs;
Agno emits the call as an AG-UI tool-call event the React layer renders.
**Tool names MUST match the `useCopilotAction({ name })` in
[`frontend/src/chat/actions.tsx`](../../frontend/src/chat/actions.tsx).**

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

### Adding a new card

1. Add a `@tool(external_execution=True)` decorated function in
   `ui_widgets.py` with the desired argument schema.
2. Mirror the name and parameters in `useCopilotAction` inside
   `frontend/src/chat/actions.tsx` using `renderAndWaitForResponse`.
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
