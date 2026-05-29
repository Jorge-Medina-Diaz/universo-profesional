# Audit Remediation — Deferred Follow-up

> Tracks items from the May-2026 full-stack audit that were intentionally
> deferred during the `audit/remediation-cosmos` work (M1–M6). Everything here
> is **medium severity or lower** and non-crashing; the critical/high bugs,
> security holes, HITL integrity, and silent-error violations were fixed in
> milestones M1–M3. Each item lists the location and why it was deferred.

## M3 — deferred (medium, mostly involved / behavioural-change)

- **ER cluster representative by `created_at`** — `coherence/application/entity_resolution.py:414` `rep = min(comp)` picks the lexicographically-smallest UUID (random for UUIDv4), not the oldest entity, so `MERGED_INTO` provenance can point the wrong way. Needs `created_at` plumbed into `_cluster_matches`. Background curator dedup only (not the agent write path); non-crashing.
- **Text2Cypher multi-column RETURN** — `graph/application/text2cypher.py` always sets `column_defs="result agtype"`, so multi-column `RETURN` queries fail. Fix = constrain the LLM system prompt to always return a single aliased agtype object. Feature-level, needs prompt + eval.
- **AG-UI `/agui/threads*` 401 propagation** — `agents/interfaces/agui_transport.py:54-55,95-96` return 200-with-empty on `UnauthorizedError` (silent). Deferred because CopilotKit v1.57 bypasses the REST 401→refresh retry, so a naive 401 could surface noisy errors on the chat-load path; needs coordinated handling.
- **AG-UI single-endpoint rate limit** — `agui_transport.py` POST `/agui` (`method=agent/run`) bypasses the 60/min Redis limiter that the REST `/agui/agent/{id}/run` path enforces.
- **`/discovery/stream` concurrency cap** — `agents/interfaces/api/router.py:267-361` has no per-user cap and opens a raw asyncpg connection per call (multi-tab exhausts the pool).
- **OAuth refresh-token reuse revocation** — `mcp_server/infrastructure/oauth_store.py:168-188` returns None on reuse but doesn't revoke the surviving token chain (mirror the identity refresh logic).
- **OAuth consent clickjacking/CSRF** — `mcp_server/interfaces/oauth_router.py:133-180` add `X-Frame-Options: DENY` + CSP `frame-ancestors 'none'` + Origin/Referer check; rate-limit + auth the DCR endpoint (`:47-78`).
- **Rate-limit bucket key collision** — `shared/rate_limit.py:38-45` keys on the last 16 chars of the JWT (can collide across users); use the decoded `sub` UUID or `sha256(token)[:32]`.
- **Revoke MCP OAuth tokens on account deletion** — `identity/application/use_cases.py:384-405` revokes browser tokens but not MCP access/refresh tokens.
- **Password-reset link hash prefix** — `identity/application/use_cases.py:334` uses `/auth/reset?token=` (404 under the hash router); should be `/#/auth/reset?token=` like email verification.
- **PDF magic-bytes BOM tolerance** — `integrations/interfaces/api/router.py:323` `startswith(b"%PDF")` rejects BOM/whitespace-prefixed valid PDFs.
- **Coherence on ALL writes (fractal principle)** — route REST entity mutations (`universe/interfaces/api/router.py:94-106`) and GitHub/LinkedIn imports (`integrations/application/github_sync.py:154-198`) through `UpsertUniverseEntity` so dedup/merge/ER/ESCO/graph-mirroring apply to manual edits too. Deferred because it changes manual-edit write semantics + latency and deserves its own focused change + tests. **High product value — schedule next.**
- **AGE-enabled Postgres in CI** — `.github/workflows/ci.yml` uses `pgvector/pgvector:pg16` (no Apache AGE); AGE-dependent migrations diverge from prod schema in CI.

## Already addressed in M2 (noted there)

- ER_REGISTRY entries for `artifact`/`architecture_decision` (graceful skip today; agent path dedups via the semantic matcher).
- `communities.py` DETACH-DELETE savepoint (Leiden ordering already correct; derived/self-healing data).
