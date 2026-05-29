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

## M4 — Net-new features ✅ SHIPPED (May 2026)

All M4 features are now built, verified, and committed on `audit/remediation-cosmos`.
Each was exercised live against the running dev stack (force-recreated container)
where possible; the two runtime gaps that genuinely can't be tested in this
environment are called out explicitly.

### MFA / TOTP — ✅ done (`feat(mfa)`)
- Native RFC 6238 TOTP in `src/shared/totp.py` (no `pyotp` dep — validated against the RFC vectors). Secret Fernet-encrypted.
- `SetupMfa`/`ConfirmMfa`/`DisableMfa` + `POST /users/me/mfa/{setup,confirm,disable}`; login MFA gate returns `{mfa_required, mfa_token}` (distinct JWT audience) → `POST /auth/mfa` exchanges code for tokens.
- FE: LoginPage code step + SettingsPage enrol/disable (replaces the "Próximamente" badge).
- **Verified live end-to-end** (register→setup→confirm→gated login→wrong-code 401→tokens→disable).

### S3 storage adapter — ✅ done (`feat(storage)`)
- `src/shared/storage.py`: `StoragePort` + `FilesystemStorageAdapter` (default; resolves legacy absolute paths) + `S3StorageAdapter` (aioboto3, lazy-imported) + cached `get_storage()` that fails loud if `s3` selected but unconfigured. Renderer renders to bytes + persists via the port (returns a relative key); downloads + avatars stream via the port.
- **Filesystem path verified live** (generate-cv → PDF/DOCX/JSON download). ⚠️ **The S3 runtime path is code-complete but unexercised here** — needs an S3 bucket + `aioboto3` installed (not in this dev container).

### Match-scoring breakdown — ✅ done (`feat(match)`)
- Shared `compute_match_breakdown` (used by `/jobs/{id}/score` + the `match_job_to_profile` MCP tool) returns grounded per-dimension scores (skills/experience/education — **no fabricated "culture" score**) + keyword coverage + gaps/strengths. FE: Popover scorecard on the Kanban badge. Fixed a latent empty-universe = 50% bug.

### JSON-Resume / Europass export — ✅ done (`feat(documents)`)
- JSON-Resume already served at `/documents/{id}/json`; now also surfaced (with DOCX) on the document viewer. **Europass**: `GET /documents/{id}/europass` maps `content_json` → the Europass CV JSON model (SkillsPassport→LearnerInfo); pure mapper, unit-tested; FE export button. Verified live.

### Reminders — ✅ done (`feat(reminders)`)
- The model/scan/routes/bell pre-existed; added the missing loop: `reminders_cron` (07:00 UTC) fans out `process_reminders_task` per user → scans + emails a `reminders_digest` (es/en) of due reminders, marks dispatched. `users.notify_email_reminders` opt-out (migration 0029) + `/users/me/notifications`. New `/reminders` page + Settings entry. Verified (worker registers task+cron, template renders, opt-out gates send).

### Application tracker — ✅ done (`feat(jobs)`)
- The Kanban already provided the status pipeline; added `next_action_at` follow-up dates that **create/dismiss `job_followup` reminders** (tracker↔reminders), `GET /jobs/{id}/documents` linking, and a card date control. Verified live (set→reminder, clear/terminal→dismissed).

### BYOK (Pro) — ✅ done (`feat(byok)`)
- `user_llm_credentials` (migration 0030, RLS) Fernet-encrypted; `GET/PUT/DELETE /agents/llm-key` (PUT Pro-gated + validated, never leaks the key). Injection: `_build_model` honours a `_byok_override` contextvar; the global cached team is untouched for non-BYOK users; `build_team_for_user` builds a per-user team (separately cached) when a key exists. FE: Pro-gated Settings card.
- **Verified**: endpoints (gating/validation/no-leak) live, and `_build_model` swaps to the BYOK key under the contextvar. ⚠️ **A full agent *run* consuming a BYOK key needs a real distinct key** (not available in dev) — the injection mechanism itself is proven.

## M5b — Deeper per-page cosmos (foundation shipped; per-page application remaining)

The token system, primitives (`glass` Card, `cta` Button, `bg-field`), shell `constellation-bg` backdrop, auth-page Fraunces+CTA, and all landing dark-mode fixes are **done**. Remaining is applying the cosmos language surface-by-surface:
- Promote `--cos-*` ↔ global tokens into a single source (currently both exist; foundation tokens added, full namespace merge pending).
- Apply `Card tone="glass"` + `Reveal`/`Stagger` entrance + Fraunces section headings to: Home, Universe inspector/HUD, Settings, Billing (use the `cta` variant on the upgrade button), Documents, GenerateCV, Compare.
- Chat surface (`ChatUI`/`FloatingChat`/HITL cards): glass panels, Fraunces card titles, gradient composer send, nova-tinted agent moments (Badge `tone="nova"`, `glow-hover-nova`).
- `ConnectionsPage`: replace raw `.card/.btn-*/.badge-*/.input` CSS classes with the DS components.
- `GenerateCvPage`: remove the duplicate template `Select`; use `ui/Select`.
- Upgrade the global `.eyebrow` to the cosmos glowing-dot + weight-600 in `SectionLabel`/`PageHeader` (deferred from M5: applying the dot globally risks clutter on small labels — make it opt-in per component).
