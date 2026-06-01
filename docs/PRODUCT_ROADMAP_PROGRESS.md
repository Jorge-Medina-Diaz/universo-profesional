# Product Roadmap — Progress & Resume-Here

Companion to [PRODUCT_ROADMAP.md](PRODUCT_ROADMAP.md) (the 12-lens deep audit:
~95 findings → 8 themes → ranked 20 + quick wins). This file records what's
**done** and a **first-steps** plan for the remainder so a fresh session can
execute without re-deriving context.

Branch: `audit/remediation-cosmos` (local only — no git remote in this
environment). Stack at last checkpoint: `/readyz` 200, **alembic head 0032**,
working tree clean.

---

## ✅ Done this pass (verified live unless noted)

| Item | Commits | Notes |
|---|---|---|
| **R1 — plan-state single source of truth** (the #1 revenue-fatal bug) | `bec0ca2`, `8d4f01c`, `fd0537b` | `premium` is now a valid **paying** tier. Root cause was 3-layered: domain only accepted `(free,pro)`, a **DB CHECK** `ck_users_tier_value` only allowed `(free,pro)`, and the Stripe webhook never mirrored `subscriptions.plan` → `users.tier`. Fixed all three: `is_paying` (pro∨premium) gate everywhere; migration 0031 widens the CHECK + backfills; webhook `_sync_user_tier()`. Backdoors closed (`set_user_tier` MCP tool + `/me/tier` refuse in prod). **Verified live**: premium passes BYOK gate (was 403). |
| **QW — mock-LLM prod guard** | `c26f023`, `79fa2f6` | `Settings.assert_llm_usable()` at every mock-construction choke point; prod-without-key raises instead of silently serving fabricated CVs. |
| **QW — 422/500 problem-detail + OAuth redirect_uri policy** | `adafc1d`, `3ddad03` | 422/500 now use the `{title,detail}` envelope; DCR rejects non-https/wildcard/fragment redirect_uris (RFC 8252, loopback http allowed). **Verified live.** |
| **R2 — FORCE RLS (policy layer)** | `f38a758`, `5c53c95` | Migration 0032 rewrites all 37 `*_user_isolation` policies with an `app.bypass_rls` service escape-hatch, then FORCEs RLS. `set_rls_user` sets the flag. **Integration test** `tests/integration/test_rls_isolation.py`. ⚠️ **Inert until the app runs as a non-owner role** — see below. |
| **QW — 402 → global upgrade modal** | `d24a48f`, `01ecdc9` | Backend already returned 402; `api.ts` now fires a `cvs:upgrade-required` event and `UpgradeModal` (mounted in `App.tsx`) offers "Ver planes". |
| **R11 — Text2Cypher tenant scoping + ontology allowlist** | `634947c`, `29442ec` | RLS does not cover AGE label tables, so the Cypher `user_id` filter is the only graph-read boundary and the LLM controlled it. Forces server `user_id`; **per-node** scope enforcement (a single binding was bypassable via a 2nd unscoped MATCH — caught by the review); ontology allowlist; read-only guard; edge-write chokepoint on `PERSONAL_EDGE_TYPES` (incl. restored `MERGED_INTO`). Tests cover the bypass vectors. |
| **R-QW — render_status on documents** (no-silent on the core CV) | `1e222e4`, `f6f2631` | `ready\|degraded\|failed` end-to-end; migration 0033 + backfill; the WeasyPrint `.html` fallback is now visible. Banner + PDF-gate on **all four** surfaces (viewer, generate-result, list, public share — the last three added in the review pass). |
| **R8+R9 — fail-loud tasks + HTTP RED metrics + worker Sentry/OTel** | `fbb350b`, `f6f2631` | `worker_failures` policy (transient→`arq.Retry`, terminal→Sentry+re-raise) on the 4 sync tasks; `cvs_http_requests_total`/`_duration` on the matched route template; worker observability init (isolated+loud); inline (Redis-down) fallback guarded; arq `--check` healthcheck. |
| **R3 — server-side onboarding/activation state** | `4d3f7e7`, `f6f2631` | `onboarding_started_at/activated_at/onboarding_completed_at` on users (migration 0034 + backfill); activation derived from real signals via raw SQL (import-linter clean); `POST /me/onboarding/advance`; FE gates read server state (Router waits on `/me` — race fixed in review); activation event now persisted to `domain_events`. |

> **All four above were independently re-reviewed by an adversarial workflow** that
> found 1 critical (the Text2Cypher multi-MATCH bypass), 1 high (the `MERGED_INTO`
> regression), and several mediums (FE degraded-PDF gaps, worker silent-except,
> Router race) — **all fixed + committed** (`29442ec`, `f6f2631`). Gates green
> (ruff F,E9 + import-linter + tsc + eslint), migrations round-trip, `/readyz` 200.

### ✅ Also shipped this pass (post-review, user-directed)
| Item | Commit | Notes |
|---|---|---|
| **R7 slice — keyset-paginate the append-only feeds** | `9a55795` | `activity` + `coherence/changes` were timestamp+LIMIT with no cursor/tiebreaker (effectively unbounded; dup/skip on equal timestamps). New `src/shared/pagination.py` (opaque cursor + `build_page`); both feeds keyset on `(ts, id)` returning a `{items, next_cursor}` envelope; FE `Page<T>` + consumers (ActivityPage, UniverseDrawer). Keyset SQL validated against live tables. |
| **R12 — ATS-readiness on the generate screen** | `6a2cc91` | On-demand match/keyword-coverage/gaps card on the CV result screen, reusing the existing `/jobs/{id}/score` endpoint (generate response now returns `job_id`). |

### ⏭ Remainder (deferred — blueprints captured)
- **R16 — interview-prep artifacts** (next user feature): per-application research
  brief / question bank / STAR drafts / mock transcripts. Large net-new build
  (prep-artifacts model + LLM generation + persistence + FE) — a focused pass.
- **F — applications first-class aggregate**: new bounded context (~13 files) +
  data-migration backfill from `jobs._tracker` + rewiring 6 call-sites + FE. A
  refactor of *working* code (the `applications` table already exists from
  migration 0001 → ALTER-not-CREATE). **Deliberately deferred** this session — the
  user prioritised perf + user-features over this refactor. Detailed blueprint saved.
- **C remainder**: jobs-list pagination (couples to F) + strict `response_model`
  typing on the paginated endpoints.
- **R10 re-sync engine + review queue**, **R13–15 agentic efficiency**, **R4 SQL
  transactional-outbox projection** (largest), **R5 AGE-in-CI** — see
  [PRODUCT_ROADMAP.md](PRODUCT_ROADMAP.md).

### ⚠️ R2 has a REQUIRED completion step (deferred, not optional)
The app connects to Postgres as **superuser `cvs`** (`rolsuper=t rolbypassrls=t`),
which bypasses RLS **even under FORCE** — so isolation is **not yet enforced**.
A `cvs_app` NOSUPERUSER NOBYPASSRLS role was **created + verified** in dev
(random user sees 0 rows, service-bypass sees all, pgvector works). The only
remaining step is pointing the app's `DATABASE_URL` at `cvs_app` (keep alembic
on `cvs`). It's a **secrets/infra change**, documented with tested commands in
[SECURITY_RLS_STATUS.md](SECURITY_RLS_STATUS.md). **Do this to actually close
the tenant-isolation hole.**

---

## ⏭ Remainder (ranked; each with first steps)

> **Process note for the next session:** the environment this pass had
> intermittent file/DB I/O garbling, which caused several `Edit` no-ops and one
> shipped-then-fixed dead feature. **Mitigations that worked:** (1) read ground
> truth via `python -c "open(...).read()"` printing raw slices before editing,
> NOT assumed structure; (2) **one Bash/Edit per turn** — parallel batches got
> cancelled en masse when the first call errored; (3) avoid `→`/unicode in
> `print()` (crashes cp1252 stdout); (4) force-recreate + gate-check after every
> migration. Alembic in-container: `docker exec cvs-backend python -m alembic
> upgrade head` (bare `alembic`/`python` resolve wrong).

### QW — `render_status` on documents  *(re-scope first — my earlier premise was WRONG)*
Goal: a failed/degraded CV render must be visible (no-silent-errors on the core
deliverable). **The domain `Document` entity has NO `render_status` field** (I
wrongly assumed it did). Real shape (verified): `documents/domain/entities.py`
`Document` ends at `created_at`; renderer falls back to writing `.html` when
WeasyPrint fails.
First steps: (1) add `render_status` to the `Document` dataclass +
`Document.create`; (2) migration `0033` add `documents.render_status text not
null default 'ready'`; (3) ORM column (`infrastructure/orm.py` `DocumentOrm`,
after `created_at`); (4) repo `add()` + `_doc_to_domain()` (module fn, NOT a
method) + `update_renders()` (it's an `update().values(...)` stmt — add the
param + a value); (5) `ports.py` `update_renders` signature; (6) `GenerateCv`
use case: derive status from `pdf_path` suffix (`.pdf`→ready / `.html`→degraded
/ none→failed) and pass to `update_renders`; (7) expose in `ListDocuments` +
`GetDocument` dicts; (8) FE `DocumentSummary` type + an amber banner in
`DocumentViewerPage`.

### R5 — Apache AGE in CI + deterministic fake-LLM for agent e2e  *(ops; CI-only, can't fully verify here)*
CI (`.github/workflows/ci.yml`) runs `pgvector/pgvector:pg16` (no AGE), so graph
tests self-skip → green build lies. First steps: (1) point the CI postgres
service at the AGE-enabled image used in compose (`docker/postgres.Dockerfile`,
published as `${POSTGRES_IMAGE}`); (2) add a `requires_age` pytest marker that
**fails** (not skips) when AGE is absent on the AGE image; (3) add a
deterministic fake-LLM provider selected when `ENV=test` so the agent loop +
tool calls + SSE framing run without a real key.

### R3 — server-side onboarding/activation state  *(migration; data-model)*
Activation truth lives in `localStorage` (`shared/onboarding.ts`) — no
cross-device, invisible to lifecycle. First steps: add
`onboarding_started_at/activated_at/completed_at` to the user/identity ORM +
migration; define the activation event (≥1 experience OR ≥3 skills OR 1 CV);
mark complete only when reached; point all gates (Router gate, LoginPage,
LinkedIn callback) at server state; keep the wizard as a deterministic fallback.

### R6 — applications first-class pipeline aggregate  *(migration + data migration)*
The Kanban tracker lives in `jobs.description_parsed._tracker` JSONB. First
steps: create an `applications` bounded context with typed columns (stage enum
Saved→Applied→Screen→Interview(n)→Offer→Closed, per-stage timestamps, notes,
contacts, linked job + documents); data-migrate the `_tracker` blob; model JD
requirements as `job_requirements` rows; retire the duplicate tracker shape.
(Note: an unused `applications` table already exists — `ApplicationOrm` — from
an earlier sprint; reconcile with it.)

### R7 — API contracts: `Page[T]` pagination + `response_model`  *(broad, mechanical)*
First steps: define a shared `Page[T]{items,total,next_cursor}` + `PageParams`;
apply keyset pagination to activity/coherence/jobs/mcp-stats; set
`response_model` on the highest-traffic resources (universe entities, documents,
jobs, snapshot); add request models for core mutations; then regenerate the TS
client via openapi-typescript.

### R8 + R9 — worker observability + fail-loud tasks + HTTP RED metrics  *(ops)*
First steps: call `init_sentry()`/`init_otel()` in `worker.startup()`; add a
worker metrics exporter + Redis-heartbeat healthcheck; gate a release on
`alembic upgrade head`; classify background-task failures (arq `Retry` w/ backoff
on transient, capture terminal to Sentry + a `failed` state); add a metrics
middleware emitting `cvs_http_requests_total` + `cvs_http_request_duration_seconds`
keyed on the matched route template.

### R11 — tenant-scope Text2Cypher/graph reads by bound param  *(security)*
Parameterize `user_id` server-side; wrap every generated Cypher in a fixed
user-bound subquery the executor controls; validate parsed queries against an
ontology-derived allowlist; centralize edge writes through one helper validating
`edge_type` against the ontology enum.

### R12 + R18 — ATS-readiness re-parse + templates; skill-gap plan loop  *(feature)*
ATS: re-parse the rendered CV for keyword coverage vs the JD + risky formatting;
surface a live score on the generate page; +2-3 ATS-safe templates. Skill-gap:
when match-scoring finds gaps, auto-generate a tracked upskilling plan (goals)
and auto-re-score as items complete.

### R10 + R19 — periodic re-sync engine + review queue; lifecycle emails  *(feature)*
Weekly per-connection GitHub/LinkedIn sync cron (reuse `run_*_sync_task`, fan
out like `reminders_cron`) → coherence/enrichment → a persistent Review queue +
Home badge. Lifecycle emails on the existing infra: Day-1 finish-setup (gated by
the R3 server activation state) + weekly new-signals digest.

### R13 / R14 / R15 — agentic efficiency  *(perf/design)*
Consolidate the ~17 near-identical CRUD specialists into 1-2 entity-curator
agents behind one `propose_entity(entity_type enum)` tool; keep only the genuine
reasoning specialists; add Anthropic prompt-cache breakpoints on the stable
system/schema prefix; move per-turn enrichment off the hot path (incremental off
`change_log` w/ a dirty flag + debounce); resolve the dup memory layer
(`factory.py:~500` TODO).

### R16 / R17 / R20 — interview-prep artifacts; job-capture + ESCO recs; complete GDPR  *(feature/security)*
Persist per-application prep artifacts (research brief, question bank, STAR
drafts, mock transcripts). Browser-extension "save this job" → Saved application;
ESCO-graph role recommendations on Home. GDPR: two-phase deletion (immediate
credential revoke incl. `OAuthStore.revoke_all_for_user` + BYOK delete + external
disconnect, then scheduled hard-erase); derive the export/erase table set
dynamically from `information_schema` + a CI test that fails when a user-scoped
table is missing.

### R4 — SQL source-of-truth transactional outbox → AGE/ESCO/snapshot/embeddings  *(LARGE; highest structural leverage)*
Derived read-models drift via best-effort dual-write. First steps: add an outbox
table written in the same txn as each SQL mutation; a worker projecting
create/update/soft-delete/merge to AGE + snapshot refresh + the embeddings
sidecar (which currently has **no writer**); route all deletes through one
gateway; add a deterministic rebuild-from-SQL reconciliation command.
