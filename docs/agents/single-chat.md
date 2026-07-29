# Single chat — pattern and limitations

Sprint 4 collapses the multi-session ChatGPT-like model into ONE persistent
chat per user. Long context is kept manageable by a hard-capped history
window plus Agno's native rolling session summary.

## Why

- The product is **about** a user's universe, not about discrete tasks.
  Multiple sessions fragment that universe and hide context the agent needs.
- Memories + the digest cover "what we've talked about" without needing
  per-thread search.
- Less UI complexity. No session list, no "new chat" button, no thread
  switcher. The chat is the home.

## Implementation

### Server-side enforcement

`backend/src/agents/interfaces/agui_router.py`:

```python
enforced_thread_id = f"main-{user_id}"
run_input.thread_id = enforced_thread_id
run_input.forwarded_props = {**(run_input.forwarded_props or {}), "user_id": str(user_id)}
```

The frontend can send whatever `thread_id` it wants — server overrides.
Agno's `team.arun(session_id=enforced_thread_id, ...)` is what actually
persists state, so a single Agno session per user is the canonical store.

### Bounded history window

`backend/src/agents/factory.py`, on the Team coordinator:

```python
add_history_to_context=True,
num_history_runs=6,
max_tool_calls_from_history=3,
```

That is the whole context bound. Agno replays the last 6 runs of the session
verbatim and keeps at most 3 historical tool calls — old tool traffic is the
real token hog, and readables re-inject current state every turn anyway.
Specialists also get `add_history_to_context=True`
(`backend/src/agents/specialists/_helpers.py`) and inherit Agno's default run
count. There is no custom windowing code: no `WINDOW_SIZE`, no message-count
threshold, no folding step.

### Session digest (Agno-native)

Everything older than the window is covered by Agno's own session summary,
enabled in `factory.py`:

```python
enable_session_summaries=True,
```

Agno maintains it as part of every run and persists it to
`ai.agno_sessions.summary` as `{"summary": str, "topics": [...]}`.
`GET /api/v1/chat/state`
(`backend/src/agents/interfaces/chat_sessions_router.py`) reads that column
and serves it as `digest`.

The earlier custom implementation — `agents/memory/sliding_window.py` and
`agents/workflows/session_digest.py`, with their `WINDOW_SIZE` /
`DIGEST_THRESHOLD` constants, the arq task and the mock-mode fallback — was
deleted in P1.C. Nothing replaced it beyond the framework feature above, and
there is no longer a `chat_session_meta.metadata.digest` write path.

### Reading the digest in chat

Frontend reads `/api/v1/chat/state` on mount and injects the digest into
`useCopilotReadable`. The agent sees:

- The recent history — via Agno's `add_history_to_context=True,
  num_history_runs=6, max_tool_calls_from_history=3`.
- The digest as a readable: "the long-tail of our conversation".
- All Agno memories (atomic facts) injected automatically.

## Trigger policy

When does the digest refresh?

- **On every run.** Agno updates the session summary as part of the turn, so
  there is nothing to schedule and nothing to invoke by hand.
- **No cron.** The old 03:30 session-digest job went away with the custom
  digest; `backend/src/shared/worker.py` no longer registers one.

## Limitations

- **Single context per user**. If the user wants to keep an "engineering"
  thread separate from "personal" they can't (yet). Tag-based filtering of
  notes covers some of this.
- **Digest fidelity**. Any rolling summary loses detail, and only the last 6
  runs survive verbatim. Older turns stay in `agno_messages`, but no agent
  tool queries that table today — there is no recovery path beyond asking the
  user again.
- **Resetting**: there's no "start over" button. Deletion would have to be
  explicit and atomic across `agno_sessions`, `agno_messages`, and
  `chat_session_meta`. Sprint 5 will add a `DELETE /api/v1/chat/state` for
  the user's right-to-be-forgotten.

## API surface

- `GET /api/v1/chat/state` — returns `{session_id, digest, message_count}`.
- `POST /agui` — main stream. Body uses AG-UI `RunAgentInput`; server
  rewrites `thread_id` and `forwarded_props.user_id`.

That's it. No `/sessions`, no `/threads`, no `/messages` CRUD.
