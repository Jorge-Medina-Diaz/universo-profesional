# Agent flow — end-to-end

Status: Sprint C (2026-05-19).

This page is the source of truth for "how does a chat message travel from
the browser to the agent and back". Read it before changing anything in
[backend/src/agents/](../../backend/src/agents/), [frontend/src/chat/](../../frontend/src/chat/),
or [frontend/src/pages/_chat/](../../frontend/src/pages/_chat/).

---

## Pipeline

```
┌────────────────────────────────────────────────────────────────────────────┐
│ Browser                                                                    │
│                                                                            │
│  HomePage                                                                  │
│   └─ CopilotSurface (frontend/src/pages/_chat/CopilotSurface.tsx)          │
│      ├─ <UniverseActions/>     ← useCopilotAction × N (HITL cards)         │
│      ├─ <UniverseReadable/>    ← useCopilotReadable × 8 (universe state)   │
│      ├─ <ChatRehydrator/>      ← seeds setMessages from /agui/threads/…/messages
│      ├─ <ChatInjector/>        ← consumes sessionStorage one-shot prompts  │
│      ├─ <ChatDropTarget>       ← drag-and-drop PDF / image into the chat   │
│      │     <CopilotChat/>      ← @copilotkit/react-ui                      │
│      │  </ChatDropTarget>                                                  │
│      └─ <SyncTaskTray/>        ← polls /sync-runs, shows live ProgressCards│
│                                                                            │
│  CopilotKit core opens an SSE stream against                                │
│       POST  ${VITE_API_BASE_URL}/agui/agent/universe_coordinator/run        │
└────────────────────────────────────────────────────────────────────────────┘
                                   ▼
┌────────────────────────────────────────────────────────────────────────────┐
│ FastAPI — backend/src/agents/interfaces/agui_router.py                     │
│                                                                            │
│  • Validates JWT, extracts user_id                                         │
│  • Forces thread_id = main-<user_id> (single-chat per user)                │
│  • Injects forwarded_props.user_id so every tool sees the user            │
│  • Streams events via ag_ui.encoder.EventEncoder (SSE)                     │
│                                                                            │
│  Also exposes (Sprint C):                                                  │
│       GET   /agui/threads                                                  │
│       GET   /agui/threads/{thread_id}/messages   ← scroll-back             │
└────────────────────────────────────────────────────────────────────────────┘
                                   ▼
┌────────────────────────────────────────────────────────────────────────────┐
│ Agno Team (universe_coordinator) — backend/src/agents/factory.py           │
│                                                                            │
│  mode="route" — coordinator LLM picks ONE member per turn                  │
│                                                                            │
│  Members (12):                                                             │
│    Entity CRUD specialists (10):                                           │
│       experience · education · project · skill · certification · course    │
│       language · achievement · interest · note                             │
│    Proactive specialists (2 — Sprint B):                                   │
│       job_strategist — opina sobre el pipeline                            │
│       cv_coach       — opina sobre los documentos generados                │
│                                                                            │
│  Coordinator tools (24):                                                   │
│    Reads     — universe_summary, find_gaps, search, get_change_history,    │
│                list_notes, list_jobs, list_documents, get_preferences,     │
│                list_reminders, get_integrations_status, get_tier           │
│    HITL/UI   — present_questionnaire, propose_github/brightdata/pdf_sync,  │
│                propose_cover_letter, present_job_match, preview_list,      │
│                confirm_destructive, upload_document_inline,                │
│                present_document_preview, present_progress, set_chat_focus  │
│                                                                            │
│  Memory (4 layers):                                                        │
│    1. Universe entities  (RLS-scoped Postgres tables)                      │
│    2. Notes              (markdown + tags)                                 │
│    3. Agno memories      (enable_agentic_memory=True)                      │
│    4. Knowledge chunks   (uploaded PDFs)                                   │
│                                                                            │
│  Sliding window 40 turns + digest workflow.                                │
└────────────────────────────────────────────────────────────────────────────┘
```

## Two flavours of tools

| Kind | Where it runs | Used for | Example |
|---|---|---|---|
| `external_execution=True` (HITL or display-only) | React (`useCopilotAction`) | Generative UI cards | `propose_experience`, `select_job_from_list`, `present_job_match` |
| Regular Agno tool | Python on backend | RLS-scoped reads/writes | `upsert_experience`, `list_jobs`, `compute_job_match` |

Both kinds coexist in the SAME agent toolset. Coherence: every write tool
(`upsert_*`, `update_preferences`, `set_job_status`) delegates to use cases
in `src/coherence/` or `src/universe/` so there's a single source of truth
for "what does it mean to add a skill" — the agent only adapts the args.

## A2UI status (Sprint C)

| Capability                              | Status | Source                                                  |
|-----------------------------------------|--------|---------------------------------------------------------|
| Tool-calls with HITL UI                 | ✅      | 22 `external_execution=True` tools, 6 generic cards      |
| Display-only tool-calls (present_*)     | ✅      | `present_job_match`, `present_document_preview`, `present_progress`, `preview_list` |
| Forms generated dynamically             | ✅      | `present_questionnaire` (4 question kinds)              |
| Selectors over lists                    | ✅      | `select_job_from_list`, `select_document_from_list`     |
| Streaming messages                      | ✅      | AG-UI SSE                                                |
| Scroll-back on reload                   | ✅      | `/agui/threads/{id}/messages` → `setMessages`            |
| Shared agent ↔ UI state (lightweight)   | ✅      | `set_chat_focus` tool + `useChatState` zustand store    |
| Drag-and-drop PDF/image into chat       | ✅      | `<ChatDropTarget>` wrapper                              |
| Long-running tasks live                 | ✅      | `<SyncTaskTray>` polls `/sync-runs` + ProgressCard       |
| Inline upload card (agent-initiated)    | ✅      | `upload_document_inline` + `<UploadInlineCard>`         |
| Full AG-UI `STATE_DELTA` sync           | ⏳      | Lightweight equivalent via `set_chat_focus` for now      |
| Multi-modal input → LLM vision payload  | ⏳      | Drag-drop persists the file; the LLM sees a text prompt about it. Sending raw image bytes to the model is the next step. |

## Scope enforcement

OAuth scopes are validated **per MCP tool call** in
[backend/src/mcp_server/interfaces/mcp_router.py](../../backend/src/mcp_server/interfaces/mcp_router.py)
lines 149–157. All 36 MCP `ToolSpec` declare a `required_scope`. RLS is
applied once per request via `set_rls_user(session, user_id)`, so the
database itself enforces tenant isolation even if a handler forgot to.

For the Agno agent, segregation is enforced by `_helpers.build_specialist()`:
each specialist only receives the toolset its `instructions=` mention, and
the coordinator only routes — it doesn't carry every tool itself.

## Where things live

- Backend agent code: [backend/src/agents/](../../backend/src/agents/)
  - `factory.py` — Team composition (cached `lru_cache(1)`)
  - `specialists/` — one file per specialist (10 entity + 2 proactive)
  - `tools/`
    - `ui_widgets.py` — HITL + display tools (`external_execution=True`)
    - `universe_reads.py`, `universe_writes.py` — entity CRUD
    - `product_reads.py`, `product_writes.py` — jobs, documents, prefs, reminders
    - `coherence_tools.py` — find_existing, change history
    - `knowledge_tools.py`, `notes_tools.py`
  - `interfaces/` — `agui_router.py` (chat stream + scroll-back), `chat_sessions_router.py`
  - `memory/sliding_window.py`, `workflows/session_digest.py`
- Frontend chat code: [frontend/src/chat/](../../frontend/src/chat/)
  - `actions.tsx` — every `useCopilotAction` (HITL handlers)
  - `readables.tsx` — `useCopilotReadable` (universe + jobs + docs + prefs + reminders + integrations + tier)
  - `state.ts` — Zustand `useChatState` for `set_chat_focus`
  - `cards/` — 12 cards (entity + generic A2UI)
  - `SyncTaskTray.tsx` — floating live-progress tray
  - `UniverseDrawer.tsx` — drawer surfacing the universe from the chat
- Frontend chat shell: [frontend/src/pages/_chat/CopilotSurface.tsx](../../frontend/src/pages/_chat/CopilotSurface.tsx)
  - The lazy entry point — everything CopilotKit-related is mounted here.
