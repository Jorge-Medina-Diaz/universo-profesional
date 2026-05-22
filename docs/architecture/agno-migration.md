# Migration: copilotkit-runtime (Node) → Agno AG-UI (FastAPI)

## Status

**Completed.** The Node `copilotkit-runtime` container has been removed entirely.
The frontend talks to Agno directly via `${VITE_API_BASE_URL}/agui` (see
[CopilotProvider.tsx](../../frontend/src/app/CopilotProvider.tsx)). There is no
optional fallback path anymore.

## What changed

| Before | After |
|---|---|
| `<CopilotKit runtimeUrl="http://copilotkit-runtime:4000/copilotkit">` | `<CopilotKit runtimeUrl="${VITE_API_BASE_URL}/agui" agent="universe_coordinator">` |
| Node CopilotRuntime with `AnthropicAdapter`/`OpenAIAdapter` | Python FastAPI `/agui` streaming SSE AG-UI events |
| Single LLM, no agents | 10 specialists + coordinator (Agno Team, `mode="route"`) |
| `/threads` stub returning empty array | Agno `agno_sessions` table + `chat_session_meta` UX metadata |
| HITL actions hooked to LLM directly | HITL actions emitted by Agno tools (`@tool(external_execution=True)`) |

## Why

1. **One backend, one auth surface.** The Node runtime had no view of our
   JWT/RLS world, so any tool call routed through it inherited the runtime's
   privileges. With Agno mounted in FastAPI we reuse `CurrentUserId` /
   `set_rls_user` directly — agents act as the authenticated user, full stop.
2. **Real agents.** The chat-first product requires multi-agent routing,
   memory, knowledge. Node CopilotRuntime is a thin LLM proxy; Agno is an
   agent framework.
3. **Less infra.** One fewer container. Shared Postgres for sessions +
   memories + knowledge.

## Migration checklist (closed)

- [x] Add `agno` + `ag-ui-protocol` + `anthropic` + `openai` to
      `backend/pyproject.toml`.
- [x] Alembic `0005_chat_sessions_meta` — UX metadata table.
- [x] `backend/src/agents/` bounded context: factory, 10 specialists, tools,
      AG-UI router with JWT auth.
- [x] `backend/src/main.py` mounts `/agui` and `/api/v1/chat/sessions`.
- [x] `frontend/src/app/CopilotProvider.tsx` points at `${API_BASE}/agui`.
- [x] `frontend/src/chat/actions.tsx` renamed to snake_case names matching
      Agno tools; `QuestionnaireCard` added for `present_questionnaire`.
- [x] **Retire `copilotkit-runtime/` container + Dockerfile + npm deps.**
- [ ] `Knowledge` (PgVector) wired for uploaded PDF/CV RAG.
- [ ] `cv_generation` Workflow integrated in `GenerateCvPage`.

## Notes for rollback

There is no longer a rollback path to the Node runtime. The folder
`copilotkit-runtime/`, the `docker/copilotkit.Dockerfile` and the
`copilotkit-runtime` service in `docker-compose.yml` have all been removed.
If you need a CopilotKit Node runtime again (e.g. for a non-Agno LLM
proxy), the old `server.ts` is recoverable from git history at commit
`57cf541` and prior.
