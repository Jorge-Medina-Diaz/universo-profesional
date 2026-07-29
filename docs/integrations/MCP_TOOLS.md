# MCP Server — Tools Reference

The Universo Profesional MCP server exposes **60 tools**.  The MCP Streamable HTTP transport (JSON-RPC 2.0 over HTTP, protocol version `2025-11-25`) is implemented directly in [`backend/src/mcp_server/interfaces/mcp_router.py`](../../backend/src/mcp_server/interfaces/mcp_router.py) — there is no MCP SDK dependency.  Authentication is OAuth 2.1 Bearer.

> **This page documents a representative subset**, not all 60. The registry in
> [`backend/src/mcp_server/application/tools.py`](../../backend/src/mcp_server/application/tools.py)
> is the source of truth — 27 of the 60 are generated per entity kind
> (`add_*` / `update_*` / `delete_*` for achievement, certification, course,
> education, experience, interest, language, project and skill). A live client can
> also just call `tools/list`, or read `/.well-known/mcp/server-card.json`.

> **Scope**: all tools are user-scoped.  Every request carries a JWT access token obtained via our OAuth 2.1 Authorization Server (RFC 8414 metadata, PKCE `S256`).  The **required scope** rows below are the `required_scope` declared on each `ToolSpec`; a call without it is rejected with JSON-RPC error `-32002`.  `ToolSpec` declares no *output* schema, so none is documented here — `tools/call` returns the handler's result JSON-serialised into a single `content` text block.

---

## Tool catalogue

### `get_universe_summary`

Returns the user's professional summary.

| | |
|---|---|
| **Description** | Compact summary: headline, counts, top skills, recent experiences, languages |
| **Input schema** | `{}` (no arguments) |
| **Required scope** | `universe:read` |

**Example call**
```json
{ "name": "get_universe_summary", "arguments": {} }
```

---

### `get_profile`

Read one section (or all) of the user's universe.

| | |
|---|---|
| **Description** | Get a section (or all) of the user's professional universe |
| **Input schema** | `{ "section?": "all" \| "education" \| "experience" \| "skill" }` (default `"all"`) |
| **Required scope** | `universe:read` |

**Example call**
```json
{ "name": "get_profile", "arguments": { "section": "experience" } }
```

---

### `search_universe`

Semantic search across the user's universe.

| | |
|---|---|
| **Description** | Semantic search across the user's universe |
| **Input schema** | `{ "query": "string", "top_k?": 10, "entity_types?": ["skill", "experience"] }` |
| **Required scope** | `universe:read` |

**Example call**
```json
{ "name": "search_universe", "arguments": { "query": "machine learning", "top_k": 5 } }
```

---

### `list_skills`

List skills with optional filters.

| | |
|---|---|
| **Description** | List skills filtered by category / min level / min years |
| **Input schema** | `{ "category?": "hard" \| "soft" \| "tool" \| "methodology", "min_level?": "basic" \| "intermediate" \| "high" \| "expert", "min_years?": 3 }` |
| **Required scope** | `universe:read` |

**Example call**
```json
{ "name": "list_skills", "arguments": { "category": "hard", "min_level": "high" } }
```

---

### `add_skill` (one of nine `add_*` tools)

Add a new entry to the universe.

| | |
|---|---|
| **Description** | Adds an entry directly — there is no proposal step on the MCP path.  One `add_*` tool exists per entity kind, each with its own argument schema. |
| **Input schema** (skill) | `{ "name": "string", "category?": "hard" \| "soft" \| "tool" \| "methodology", "level?": "basic" \| "intermediate" \| "high" \| "expert", "years?": 5, "last_used_year?": 2025 }` |
| **Required scope** | `universe:write` |

**Example call**
```json
{
  "name": "add_experience",
  "arguments": { "org": "Acme", "role": "Senior Dev", "start_date": "2024-01" }
}
```

---

### `update_skill` (one of nine `update_*` tools)

Patch an existing entry.

| | |
|---|---|
| **Description** | Patch an existing entity by id.  The schema accepts the same fields as the matching `add_*` tool, all optional, plus `additionalProperties`. |
| **Input schema** (skill) | `{ "id": "uuid", "name?": "string", "category?": "...", "level?": "...", "years?": 5, "last_used_year?": 2025 }` |
| **Required scope** | `universe:write` |

**Example call**
```json
{
  "name": "update_skill",
  "arguments": { "id": "a1b2c3d4-...", "level": "expert", "years": 5 }
}
```

---

### `delete_skill` (one of nine `delete_*` tools)

Remove an entry from the universe.

| | |
|---|---|
| **Description** | Removes the entity by id.  Gated behind its own scope, which is **not** granted by default. |
| **Input schema** | `{ "id": "uuid" }` |
| **Required scope** | `universe:delete` |

**Example call**
```json
{ "name": "delete_project", "arguments": { "id": "a1b2c3d4-..." } }
```

---

### `link_evidence`

Attach a skill to the entity that evidences it.

| | |
|---|---|
| **Description** | Link a skill to an evidence entity (experience/project/etc) |
| **Input schema** | `{ "skill_id": "uuid", "evidence_entity_type": "string", "evidence_entity_id": "uuid", "weight?": 1.0, "notes?": "string" }` |
| **Required scope** | `evidence:write` |

**Example call**
```json
{
  "name": "link_evidence",
  "arguments": {
    "skill_id": "a1b2c3d4-...",
    "evidence_entity_type": "project",
    "evidence_entity_id": "e5f6a7b8-..."
  }
}
```

---

### `get_activity`

Return recent universe activity.

| | |
|---|---|
| **Description** | Return recent universe activity |
| **Input schema** | `{ "limit?": 50, "since?": "2026-01-01T00:00:00Z", "event_types?": ["..."] }` |
| **Required scope** | `universe:read` |

**Example call**
```json
{ "name": "get_activity", "arguments": { "limit": 20 } }
```

---

### `generate_cv`

Generate a CV from universe data.

| | |
|---|---|
| **Description** | Generate an ATS-adapted CV (PDF + DOCX + JSON Resume).  Optionally tailors to a job description. |
| **Input schema** | `{ "job_url?": "...", "job_description?": "...", "template?": "ats-classic", "language?": "es" \| "en", "tone?": "string", "length?": "1-page" \| "2-page" }` |
| **Required scope** | `documents:generate` |

**Example call**
```json
{
  "name": "generate_cv",
  "arguments": {
    "job_description": "Senior backend engineer with Python...",
    "template": "modern",
    "language": "es",
    "length": "2-page"
  }
}
```

---

## OAuth 2.1 flow (brief)

1. **Metadata discovery** — `GET /.well-known/oauth-authorization-server` (RFC 8414) and `GET /.well-known/oauth-protected-resource` (RFC 9728).
2. **Dynamic Client Registration** — `POST /auth/oauth/register` (RFC 7591) → `client_id`.  Only public clients are supported (`token_endpoint_auth_method: "none"`, PKCE-only).
3. **Authorization request** — `GET /auth/oauth/authorize` renders the consent screen, `POST /auth/oauth/authorize` records the decision.  `response_type=code` + PKCE `code_challenge` with `S256` (RFC 7636).
4. **Token exchange** — `POST /auth/oauth/token` → `access_token` (JWT, `aud` = the MCP canonical URI) + `refresh_token`.  Supported grants: `authorization_code`, `refresh_token`.  Revoke with `POST /auth/oauth/revoke`.
5. **MCP calls** — include `Authorization: Bearer <access_token>`.  Signing keys are published at `GET /.well-known/jwks.json`.

There is no DPoP / sender-constrained-token support; bearer tokens are used as-is.

[`backend/src/mcp_server/domain/scopes.py`](../../backend/src/mcp_server/domain/scopes.py) declares **20 scopes**, 18 of which are granted by default (`universe:delete` and `account:write` must be requested explicitly).  Which one a tool needs is per-tool (see the tables above).  The access token carries the user id in its `sub` claim; the MCP server never asks for a user identifier in the tool arguments.

---

## Transport endpoint

```
POST /mcp
Authorization: Bearer <jwt>
Content-Type: application/json
```

A single JSON-RPC 2.0 endpoint (also reachable as `/mcp/`).  Supported methods: `initialize`, `notifications/initialized`, `tools/list`, `tools/call`, `resources/list`, `resources/read`.  Responses are plain `application/json` — there is no SSE stream, no heartbeat and no `Last-Event-ID` resumption.  An unauthenticated call returns `401` with `WWW-Authenticate: Bearer … resource_metadata="…/.well-known/oauth-protected-resource"`, pointing the client at the metadata document.

---

## Write path

MCP write tools mutate directly: the handler runs the same use case the REST API uses, inside the request's unit of work, with RLS pinned to the token's `sub`, and the transaction is committed when the handler returns.  No proposal is created and nothing else has to confirm the change.

Every successful `tools/call` consumes one `mcp_call` from the user's daily quota (the free tier has no MCP access at all); failed calls do not burn the allowance.

The HITL proposal flow (`backend/src/agents/infrastructure/proposal_store.py` → `POST /api/v1/coherence/upsert`) belongs to the in-app agent, **not** to MCP.
