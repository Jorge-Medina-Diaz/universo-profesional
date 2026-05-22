# Single chat — pattern and limitations

Sprint 4 collapses the multi-session ChatGPT-like model into ONE persistent
chat per user. Long context is kept manageable by a sliding window + a
periodically-refreshed structured digest.

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

### Sliding window

`backend/src/agents/memory/sliding_window.py`:

- `WINDOW_SIZE = 40` — most recent N messages kept verbatim in the LLM
  context.
- `DIGEST_THRESHOLD = 60` — once `count(messages) ≥ 60`, the older N-40
  messages get folded into the digest.

### Session digest

`backend/src/agents/workflows/session_digest.py` runs as an arq task. For
each user with messages beyond the threshold:

1. Pull the older-than-window messages.
2. Call the LLM with structured-output instructions:
   ```
   {open_questions, decisions, mentioned_entities, mentioned_topics}
   ```
3. Persist into `chat_session_meta.metadata.digest` (JSONB).

Mock mode (no LLM key) uses a deterministic fallback that extracts uppercase
tokens as "entities" and `?`-containing messages as "open questions". Lossy
but keeps dev flows interactive.

### Reading the digest in chat

Frontend reads `/api/v1/chat/state` on mount and injects the digest into
`useCopilotReadable`. The agent sees:

- The full sliding window (~40 latest messages) — via Agno's
  `add_history_to_context=True, num_history_runs=8`.
- The digest as a readable: "the long-tail of our conversation".
- All Agno memories (atomic facts) injected automatically.

## Trigger policy

When does the digest workflow run?

- **Daily cron**: not implemented in Sprint 4 (added in Sprint 5).
- **On demand**: any handler can call `run_session_digest(user_id=...)`.
  For now it's queued via arq when a chat session exceeds `DIGEST_THRESHOLD`
  — wiring is in the worker but the chat hook is a follow-up.

## Limitations

- **Single context per user**. If the user wants to keep an "engineering"
  thread separate from "personal" they can't (yet). Tag-based filtering of
  notes covers some of this.
- **Digest fidelity**. Even with Sonnet, summarizing into 800 tokens loses
  detail. Recovery path: search `agno_messages` directly via tools when the
  agent needs specifics.
- **Resetting**: there's no "start over" button. Deletion would have to be
  explicit and atomic across `agno_sessions`, `agno_messages`, and
  `chat_session_meta`. Sprint 5 will add a `DELETE /api/v1/chat/state` for
  the user's right-to-be-forgotten.

## API surface

- `GET /api/v1/chat/state` — returns `{session_id, digest, message_count}`.
- `POST /agui` — main stream. Body uses AG-UI `RunAgentInput`; server
  rewrites `thread_id` and `forwarded_props.user_id`.

That's it. No `/sessions`, no `/threads`, no `/messages` CRUD.
