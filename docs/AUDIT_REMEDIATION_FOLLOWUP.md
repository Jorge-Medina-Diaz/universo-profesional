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

---

## M4 — Net-new features (greenfield; not started — execution spec)

These are new product capabilities (the user opted into "everything incl. net-new"). They were **not** half-built: shipping partial backend endpoints / broken UI affordances would re-introduce the exact issues the audit flagged, and the backend can't be exercised end-to-end through the Windows bind-mount-limited dev container. Each below is scoped and ready to build as a focused, independently-verifiable change.

### MFA / TOTP (highest value — security; fixes the SettingsPage affordance)
- Fields already exist: `User.mfa_secret`, `User.mfa_enabled` (domain + ORM) — **no migration needed**. `pyotp` is already a dependency; encrypt the secret with the existing Fernet `TOKEN_ENCRYPTION_KEY`.
- Backend (identity): `POST /me/mfa/setup` → generate secret, store encrypted (enabled=False), return `otpauth://` URI + secret; `POST /me/mfa/verify` → `pyotp.TOTP(secret).verify(code)`, set `mfa_enabled=True`; `POST /me/mfa/disable` → verify code/password, clear secret + flag.
- **Login challenge (the risky part — touches core auth):** `Login.execute` returns `{mfa_required: true, mfa_token}` (short-lived) when `mfa_enabled`; new `POST /auth/mfa-challenge` exchanges `mfa_token` + code for the real token pair. Verify thoroughly (login is critical-path).
- FE: SettingsPage enrol (QR via a lib-free `<img>` to a QR data-URL or text secret) → verify → enabled; disable flow. Replace the "Próximamente" badge (set in M4-partial) with the live toggle.

### S3 storage adapter (production durability)
- `config.storage_provider="s3"` is accepted but no impl exists → files on ephemeral disk are lost on redeploy. Implement `S3StorageAdapter(aioboto3)` behind the existing `StoragePort`; wire into renderer + file-download endpoints; keep `FilesystemStorageAdapter` for local dev (MinIO optional). Add a startup assertion if `storage_provider=s3` but unconfigured. Needs bucket/IAM provisioning.

### Match-scoring breakdown (contained, FE-leaning)
- `jobs.computeScore(id)` currently surfaces only a single `match_score` %. Extend the backend match use case to return per-dimension scores (skills / experience / education / culture), then render them in a popover on `JobsPage` `KanbanCard` (hover the score badge). Confirm the backend response shape first — if it only returns a number, the dimensional compute is the bulk of the work.

### JSON-Resume / Europass export (interoperability)
- CV generation already produces `json_resume`. Add a validated **JSON-Resume** download (endpoint returns the stored `content_json` as a downloadable file; FE export menu button). **Europass** = a v3 JSON-LD schema mapping from the universe entities — larger; build after JSON-Resume.

### Application tracker · Reminders · BYOK (need product design first)
- Each is a mini-product (new bounded context / module + UI). Per the plan they warrant a brief brainstorm before building (status pipeline shape for the tracker; reminder triggers/cadence + arq scheduling; BYOK key storage + provider-switch UX). Build each as its own slice with its own migration, RLS, and tests. App-tracker + reminders should route writes through the coherence engine (fractal principle).

## M5b — Deeper per-page cosmos (foundation shipped; per-page application remaining)

The token system, primitives (`glass` Card, `cta` Button, `bg-field`), shell `constellation-bg` backdrop, auth-page Fraunces+CTA, and all landing dark-mode fixes are **done**. Remaining is applying the cosmos language surface-by-surface:
- Promote `--cos-*` ↔ global tokens into a single source (currently both exist; foundation tokens added, full namespace merge pending).
- Apply `Card tone="glass"` + `Reveal`/`Stagger` entrance + Fraunces section headings to: Home, Universe inspector/HUD, Settings, Billing (use the `cta` variant on the upgrade button), Documents, GenerateCV, Compare.
- Chat surface (`ChatUI`/`FloatingChat`/HITL cards): glass panels, Fraunces card titles, gradient composer send, nova-tinted agent moments (Badge `tone="nova"`, `glow-hover-nova`).
- `ConnectionsPage`: replace raw `.card/.btn-*/.badge-*/.input` CSS classes with the DS components.
- `GenerateCvPage`: remove the duplicate template `Select`; use `ui/Select`.
- Upgrade the global `.eyebrow` to the cosmos glowing-dot + weight-600 in `SectionLabel`/`PageHeader` (deferred from M5: applying the dot globally risks clutter on small labels — make it opt-in per component).
