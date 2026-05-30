# Audit Remediation — Deferred Follow-up

> Tracks items from the May-2026 full-stack audit that were intentionally
> deferred during the `audit/remediation-cosmos` work (M1–M6). Everything here
> is **medium severity or lower** and non-crashing; the critical/high bugs,
> security holes, HITL integrity, and silent-error violations were fixed in
> milestones M1–M3. Each item lists the location and why it was deferred.

## M3 — deferred → ✅ MOSTLY DONE (May 2026, batches 1-2)

11 of the 13 deferred items are now implemented + committed (`fix(security)` batches
1-2). The two genuinely-large/risky ones remain, with refined scoping below.

**Done:** ER representative by `created_at` · Text2Cypher multi-column RETURN ·
AG-UI 401 now logged (not silent) + `/agui` run path through the limiter ·
`/discovery/stream` per-user cap (2) · OAuth refresh-reuse chain revocation ·
OAuth consent Origin/Referer CSRF check (clickjacking headers were already
global) · DCR `/register` 10/hour rate-limit · rate-limit bucket key → stable
`sub` claim · revoke MCP tokens on account deletion (instant — bearer path
checks `revoked_at`) · password-reset hash link **+ the entire missing FE flow**
(ForgotPassword/ResetPassword pages, routes, api, login link) · PDF BOM-tolerant
magic-bytes.

### Remaining — 2 items (need their own focused change)

- **Coherence on ALL writes (fractal principle)** — route REST entity mutations
  (`universe/interfaces/api/router.py` `add_*`) and GitHub/LinkedIn imports
  (`integrations/application/github_sync.py`, `linkedin_csv_deep.py`) through
  `UpsertUniverseEntity` (clean wiring exists — see `agents/tools/universe_writes.py:46-61`).
  **Not a blind reroute** — two design issues found during this pass:
  1. **Import identity ≠ semantic identity.** GitHub dedups by repo **URL** and
     LinkedIn by profile URL — exact identity. The ER pipeline matches
     semantically/by-name, so dropping the URL dedup (as a naive reroute would)
     risks **merging two distinct repos**. The funnel must take the URL as a
     strong blocking key, or keep URL dedup and layer coherence on top. Skills /
     interests / experiences (fuzzy, no URL identity) are the safe-to-reroute
     subset and benefit most (ESCO linking + semantic dedup).
  2. **REST contract change.** `SkillCrud.add` 409s on a duplicate name; through
     the funnel that becomes a silent merge, and `UpsertOutcome` can be
     `SUGGESTED` (nothing created). The `add_*` handlers + frontend need to
     handle `CREATED`/`MERGED`/`SUGGESTED` outcomes (today they expect the entity
     back). Needs FE coordination + tests. **High product value — schedule as a
     dedicated change.**
- **AGE-enabled Postgres in CI** — `.github/workflows/ci.yml` uses
  `pgvector/pgvector:pg16` (no Apache AGE), so AGE-dependent migrations/tests
  diverge from prod in CI. Needs a CI service image carrying **both** pgvector
  and AGE (the prod image already does) — an infra/image task, not app code.

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
