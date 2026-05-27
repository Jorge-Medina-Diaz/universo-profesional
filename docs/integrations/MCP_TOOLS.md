# MCP Server — Tools Reference

The Universo Profesional MCP server exposes **10 tools** through the official MCP Python SDK (`mcp>=1.1.0`).  Transport is HTTP streamable (SSE endpoint) with OAuth 2.1 authentication.

> **Scope**: all tools are user-scoped.  Every request carries a JWT access token obtained via our OAuth 2.1 Authorization Server (RFC 8414 metadata, PKCE, DPoP).  Write operations never mutate data directly — they create **proposals** that the user confirms through the HITL flow.

---

## Tool catalogue

### `read_universe_summary`

Returns the user's professional summary.

| | |
|---|---|
| **Description** | Headline, entity counts, top skills, recent experiences, languages, preferences |
| **Input schema** | `{}` (no arguments) |
| **Output schema** | `{ "headline": "...", "counts": {...}, "top_skills": [...], "recent_experiences": [...], "languages": [...] }` |
| **Required scope** | `universe:read` |

**Example call**
```json
{ "name": "read_universe_summary", "arguments": {} }
```

---

### `read_entity`

Read a specific entity by type and ID or name.

| | |
|---|---|
| **Description** | Fetch one entity from the user's universe |
| **Input schema** | `{ "entity_type": "skill", "id?": "uuid", "name?": "string" }` |
| **Output schema** | `{ "entity": { ... } }` or `{ "entities": [...] }` when querying by name |
| **Required scope** | `universe:read` |

**Example call**
```json
{ "name": "read_entity", "arguments": { "entity_type": "skill", "name": "Python" } }
```

---

### `search_entities`

Semantic search across the user's universe.

| | |
|---|---|
| **Description** | Keyword/phrase search with pgvector semantic ranking |
| **Input schema** | `{ "query": "string", "top_k?": 10, "entity_types?": ["skill", "experience"] }` |
| **Output schema** | `[{ "id": "...", "kind": "...", "name": "...", "score": 0.92 }]` |
| **Required scope** | `universe:read` |

**Example call**
```json
{ "name": "search_entities", "arguments": { "query": "machine learning", "top_k": 5 } }
```

---

### `list_entities`

List all entities of a given type.

| | |
|---|---|
| **Description** | Enumerate every entity of a kind (e.g. all skills) |
| **Input schema** | `{ "entity_type": "skill" }` |
| **Output schema** | `[{ ...entity fields... }]` |
| **Required scope** | `universe:read` |

**Example call**
```json
{ "name": "list_entities", "arguments": { "entity_type": "project" } }
```

---

### `create_entity`

Propose the creation of a new entity (HITL).

| | |
|---|---|
| **Description** | Creates a proposal stored in `proposal_store.py`. The user must confirm via the HITL UI before persistence. |
| **Input schema** | `{ "entity_type": "string", "data": {...}, "confidence?": 0.85, "reason?": "string" }` |
| **Output schema** | `{ "proposal_id": "uuid", "action": "create", "entity_type": "...", "entity_data": {...}, "message": "..." }` |
| **Required scope** | `universe:write` |

**Example call**
```json
{
  "name": "create_entity",
  "arguments": {
    "entity_type": "experience",
    "data": { "org": "Acme", "role": "Senior Dev", "start_date": "2024-01" },
    "confidence": 0.9,
    "reason": "User mentioned this role in chat"
  }
}
```

---

### `update_entity`

Propose an update to an existing entity (HITL).

| | |
|---|---|
| **Description** | Creates an update proposal.  The user reviews a diff card before committing. |
| **Input schema** | `{ "entity_type": "string", "entity_id": "uuid", "data": {...}, "confidence?": 0.85, "reason?": "string" }` |
| **Output schema** | `{ "proposal_id": "uuid", "action": "update", "entity_type": "...", "entity_id": "...", "patch": {...} }` |
| **Required scope** | `universe:write` |

**Example call**
```json
{
  "name": "update_entity",
  "arguments": {
    "entity_type": "skill",
    "entity_id": "a1b2c3d4-...",
    "data": { "level": "expert", "years": 5 },
    "reason": "User confirmed 5 years of experience"
  }
}
```

---

### `delete_entity`

Propose deletion of an existing entity (HITL).

| | |
|---|---|
| **Description** | Creates a delete proposal.  Requires explicit user confirmation. |
| **Input schema** | `{ "entity_type": "string", "entity_id": "uuid", "reason?": "string" }` |
| **Output schema** | `{ "proposal_id": "uuid", "action": "delete", "entity_type": "...", "entity_id": "..." }` |
| **Required scope** | `universe:delete` |

**Example call**
```json
{
  "name": "delete_entity",
  "arguments": {
    "entity_type": "project",
    "entity_id": "a1b2c3d4-...",
    "reason": "User said the project was cancelled"
  }
}
```

---

### `link_esco`

Link free-text to the ESCO ontology.

| | |
|---|---|
| **Description** | Runs the ESCO linker pipeline (embed → pgvector → `FeatureReranker` → threshold). Returns `LINKED`, `SUGGESTED`, `ORPHAN` or `ERROR`. |
| **Input schema** | `{ "text": "string", "kind?": "skill" | "occupation" }` |
| **Output schema** | `{ "state": "LINKED", "esco_uri": "...", "score": 0.91, "reason": "...", "candidates": [...] }` |
| **Required scope** | `universe:write` |

**Example call**
```json
{ "name": "link_esco", "arguments": { "text": "Docker", "kind": "skill" } }
```

---

### `get_discovery_progress`

Return discovery score and profile growth metrics.

| | |
|---|---|
| **Description** | Score 0-100, entity counts, coverage per dimension, recent activity, ESCO link stats |
| **Input schema** | `{}` (no arguments) |
| **Output schema** | `{ "discovery_score": 72, "counts": {...}, "coverage": {...}, "sparse_dimensions": [...], "recent_discoveries": [...], "esco_links": {...} }` |
| **Required scope** | `universe:read` |

**Example call**
```json
{ "name": "get_discovery_progress", "arguments": {} }
```

---

### `generate_cv`

Generate a CV from universe data.

| | |
|---|---|
| **Description** | Produces PDF, DOCX and JSON Resume from the user's profile.  Optionally tailors to a job description. |
| **Input schema** | `{ "job_url?": "...", "job_description?": "...", "template?": "ats-classic", "language?": "es" | "en", "tone?": "string", "length?": "1-page" | "2-page" }` |
| **Output schema** | `{ "document_id": "uuid", "pdf_url": "...", "docx_url": "...", "json_resume": {...} }` |
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

1. **Metadata discovery** — `GET /.well-known/oauth-authorization-server` (RFC 8414).
2. **Dynamic Client Registration** — `POST /oauth/register` (RFC 7591) → `client_id`.
3. **Authorization request** — `response_type=code` + PKCE `code_challenge` (RFC 7636) + DPoP proof (RFC 9449).
4. **Token exchange** — `POST /oauth/token` → `access_token` (JWT) + `refresh_token`.
5. **MCP calls** — include `Authorization: Bearer <access_token>` + DPoP proof header.

Scopes required depend on the tool (see table above).  The access token carries the `user_id` claim; the MCP server never asks for a user identifier in the tool arguments.

---

## SSE transport endpoint

```
GET /mcp/sse
Authorization: Bearer <jwt>
```

The server opens a text/event-stream connection and emits JSON-RPC messages wrapped in SSE `data:` lines.  Keep-alive comments (`:heartbeat`) are sent every 15 seconds to prevent proxy timeouts.  The client reconnects automatically with `Last-Event-ID` on disconnect.

---

## HITL proposal flow

All write tools (`create_entity`, `update_entity`, `delete_entity`) return a `proposal_id`.  The client must:

1. Present the proposal to the user (React card).
2. On confirm → `POST /api/v1/coherence/upsert` with the proposal payload.
3. On reject/edit → `POST /api/v1/agents/feedback` to feed the self-learning loop.

No data is mutated until step 2.
