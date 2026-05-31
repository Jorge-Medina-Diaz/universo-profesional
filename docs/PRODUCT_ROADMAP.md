# Product Deep-Audit Roadmap

> Generated from a 12-lens principal-level audit (career-product, onboarding,
> monetization, data-model, API, performance, agentic, frontend, UX, security,
> observability, testing) → ~95 findings deduped into 8 themes + a ranked roadmap.
> This goes beyond bugs: design flaws, scale risks, and missing product capabilities.

## Executive summary

The 12-lens audit surfaced ~95 distinct findings that collapse into 8 root themes once deduplicated. The single most important conclusion: the product has impressive surface area (26-specialist Agno team, AGE graph, ESCO ontology, MCP, billing, embeddings) but several load-bearing foundations are quietly broken or fictional, and the end-to-end job-seeker funnel stops at "generate a CV." Three issues are revenue- or trust-fatal and must lead: (1) paid users are denied Pro features because users.tier and subscriptions.plan are never reconciled and 'premium' literally cannot be stored; (2) Row-Level Security is never FORCEd and the app connects as the table owner, so tenant isolation is silently bypassable in production; (3) onboarding/activation truth lives in localStorage and can be "completed" with zero data, so there is no activation gate, no cross-device state, and no lifecycle/retention engine. Compounding these, the graph/ontology/snapshot read-models are kept in sync by best-effort dual-writes with no outbox — meaning the agent's "connective tissue" (RELATED_TO, embeddings sidecar) queries partly empty/stale data, while CI runs without Apache AGE so every graph test self-skips on a green build (the build is lying). The roadmap is sequenced so foundation fixes (billing truth, RLS, onboarding state, outbox/projection, AGE-in-CI, API contracts, worker observability) land first because they unblock or de-risk almost everything above them, followed by the genuinely missing funnel features (first-class application pipeline, job capture, interview-prep artifacts, ATS re-scoring, skill-gap plans) that turn a CV generator into a career platform. I deliberately dropped or down-ranked ~15 low-value/over-engineered findings (status-code purism, Diff model typing, BYOK cache thrash, API-version centralization, MCP overage metering, Fernet rotation) so effort concentrates where value-per-effort and downstream leverage are highest. Several adversarially-validated quick wins (kill the tier dev-backdoor + set_user_tier MCP escalation, 402 upgrade prompts, transactional PDF import, redirect_uri validation, render-failure status) deliver outsized value in days.

## Themes

- **Monetization truth & plan coherence** (8 findings) — Two unreconciled plan-state systems deny paying users Pro features and 'premium' can't even be stored — billing is leaking revenue and trust
- **Tenant isolation & security correctness** (7 findings) — RLS is never FORCEd, the app runs as table owner, Text2Cypher trusts the model for scoping, and an MCP tool lets free users self-escalate to Pro
- **Onboarding, activation & retention loops** (11 findings) — Activation is a localStorage fiction with two competing flows, no server truth, no re-sync engine, and no lifecycle email beyond reminders
- **Data-model integrity & projection (SQL→graph/embeddings/snapshot)** (10 findings) — Derived read-models drift via best-effort dual-write with no outbox/reconciliation; an embeddings sidecar has no writer; trackers/JD requirements rot in unindexed JSONB
- **End-to-end job-seeker funnel completeness** (9 findings) — The funnel opens at 'paste a JD' and ends at 'here's a CV' — no job capture, first-class application pipeline, interview-prep artifacts, ATS re-scoring, skill-gap plans, or offer/negotiation
- **API contracts & scale ceilings** (11 findings) — Few response models, no real pagination, inconsistent envelopes, split error contract, untyped write bodies, and a 15-connection DB pool fronting API + SSE + Agno + AGE
- **Observability, reliability & CI honesty** (12 findings) — Worker tier is observability-dark, background tasks swallow exceptions (so nothing retries), no RED metrics, no migration step in deploy, and CI lacks AGE so graph tests self-skip green
- **Agentic system efficiency & correctness** (9 findings) — 26 specialists (≈17 near-identical CRUD agents) inflate route latency/cost, no prompt caching on a huge stable prefix, three overlapping memory layers, and a global single Team cache with no concurrency proof

## Quick wins

- **[S] Remove the /users/me/tier dev backdoor and the set_user_tier MCP tool from production** (Security & Monetization) — Free users can currently self-escalate to Pro via an MCP tool and an unguarded tier endpoint — direct revenue leak and privilege escalation. Gate both behind a dev-only flag and make tier strictly server-derived from Stripe. Hours of work, closes a paid-feature bypass.
- **[M] Standardize quota denial as HTTP 402 + a reusable 'quota reached → upgrade' modal** (Monetization) — Quotas are enforced but never converted into an upgrade moment in the CV/cover-letter/chat flows. Reusing the machine-readable body require_pro_tier already emits turns every hard wall into a conversion surface — the cheapest revenue lever in the audit.
- **[S] Switch PDF import to the existing transactional /pdf/parse → /pdf/commit endpoint** (Onboarding) — The wizard commits entities one-at-a-time client-side despite a transactional server endpoint already existing, causing N-request fan-out and 'algunas no se pudieron' partial failures at the single most fragile activation moment. One-line-of-intent change, big reliability win.
- **[S] Persist a render status (queued/rendering/ready/failed+error) on the document row** (Reliability) — A failed CV/cover-letter render is currently both un-retried and invisible — a direct violation of the no-silent-errors rule on the core deliverable. A status field + UI surface makes failures actionable in under a day.
- **[S] Enforce redirect_uri policy at OAuth Dynamic Client Registration and authorize** (Security) — DCR accepts arbitrary redirect_uris (open redirect → token exfiltration). Require https (loopback http exception per RFC 8252), reject wildcards/fragments. Small, well-bounded fix to a high-severity token-theft vector.
- **[S] Add RequestValidationError + last-resort Exception handlers emitting the existing problem-detail envelope** (API contracts) — 422 and 500 currently fall back to framework defaults while only DomainError/RateLimit get problem-detail. Two handlers reusing the existing envelope (with X-Request-Id) make the entire API error contract consistent in hours.
- **[S] Gate the mock LLM provider behind an explicit dev/test allow flag** (Agentic safety) — The mock provider can silently serve fabricated CV content in any environment when no key resolves. In prod-with-no-key it must raise a user-visible error, not invent a CV. Small guard, prevents shipping hallucinated deliverables.

## Ranked roadmap

### #1 — Collapse plan state to a single source of truth (subscription-derived tier)  `[critical/M]`
*Theme: Monetization truth & plan coherence · kind: data_model*

**Why:** Paid users are actively denied Pro features today because require_pro_tier/BYOK/Bright Data read users.tier while Stripe updates subscriptions.plan, and 'premium' cannot even be stored in users.tier. This is silent revenue loss plus guaranteed churn — the worst class of bug. Fixing it unblocks every downstream monetization item (quota prompts, usage meters, MCP gating) and makes the dev-backdoor removal safe.

**First steps:** Make is_paying (covering pro+premium) the single gate read by all entitlement checks; have the Stripe webhook be the only writer of canonical entitlement; backfill/reconcile existing users.tier from subscriptions; add a test asserting a paying subscriber passes every Pro gate.

### #2 — FORCE Row-Level Security and run the app as a non-owner RLS-subject role  `[critical/M]`
*Theme: Tenant isolation & security correctness · kind: security*

**Why:** RLS policies exist but are never FORCEd and the app connects as the table owner, so tenant isolation is silently bypassable in production — a single bug or injection leaks cross-user career data. Cheap relative to blast radius and a prerequisite for trustworthy multi-tenant scale; also makes the DB-level RLS test meaningful.

**First steps:** Add a migration issuing ALTER TABLE ... FORCE ROW LEVEL SECURITY for every user-scoped table; provision a dedicated NOINHERIT non-owner role for the app; add a DB-policy test that sets app.current_user_id for user A and asserts direct SELECT/UPDATE/DELETE on user B rows returns nothing.

### #3 — Make onboarding/activation state server-side with one canonical flow and a real activation gate  `[critical/M]`
*Theme: Onboarding, activation & retention loops · kind: design*

**Why:** Six findings collapse here: onboarding can complete with zero data, truth lives in localStorage (breaks cross-device, invisible to lifecycle), two flows both 'complete', and the gate is faked on page arrival. Server truth (onboarding_started_at/activated_at/completed_at) plus an explicit activation event (>=1 experience OR >=3 skills OR 1 CV) is the keystone that unblocks lifecycle emails, funnel analytics, and retention — nothing else in retention works without it.

**First steps:** Add onboarding/activation columns to the identity ORM; define the activation event and only mark complete when reached; pick the chat flow as canonical and point all entry paths (router gate, LoginPage, LinkedIn callback) at it; make the wizard a deterministic fallback; drive the gate off server state.

### #4 — Make SQL the source of truth with a transactional outbox projecting to AGE/ESCO/snapshot/embeddings  `[critical/L]`
*Theme: Data-model integrity & projection · kind: design*

**Why:** The graph, ontology, snapshot, and embeddings are derived read-models synced by best-effort dual-write with no outbox or reconciliation — they drift, soft-deletes don't propagate, and the change-log is partial and never replayed. This single architectural correction subsumes five findings and makes the agent's graph reads trustworthy, which everything agentic depends on. Highest-leverage structural fix even though it is large.

**First steps:** Add an outbox table written in the same transaction as each SQL mutation; build a worker that projects create/update/soft-delete/merge to AGE, refreshes the snapshot, and writes the embeddings sidecar (which currently has NO writer); route all deletes through one gateway; add a deterministic rebuild-from-SQL command for reconciliation.

### #5 — Put Apache AGE in CI and add a deterministic fake-LLM provider for agent e2e  `[critical/M]`
*Theme: Observability, reliability & CI honesty · kind: ops*

**Why:** CI runs Postgres without AGE, so the entire graph/Cypher engine self-skips on a green build — the build is lying about the product's core differentiator, and the agent run + BYOK decrypt path is unexercised end-to-end. Until builds tell the truth, every other change to graph/agentic code ships blind. This unblocks safe iteration on themes 4, 7, and 8.

**First steps:** Point ci.yml's postgres service at the already-built ghcr.io/jorgemr/cvs-postgres:pg16 image; add a requires_age marker that fails (not skips) when AGE is absent on the AGE-enabled image; add a fake-LLM provider selected when ENV=test to exercise the agent loop, tool calls, and SSE framing without a real key.

### #6 — Promote applications to a first-class pipeline aggregate with a typed stage state machine  `[high/M]`
*Theme: End-to-end job-seeker funnel completeness · kind: design*

**Why:** The application tracker is an untyped JSONB side-channel on the documents context (two findings: product + data-model). It is the spine of the entire apply→track→prep funnel that competitors (Teal/Huntr) win on, yet it is unindexed and unqueryable. Promoting it unblocks job capture, interview prep artifacts, networking, and lifecycle nudges that all hang off application state.

**First steps:** Create an applications bounded context with typed columns (stage enum Saved→Applied→Screen→Interview(n)→Offer→Closed, per-stage timestamps, contacts, tasks, notes); migrate the _tracker JSONB blob; model JD requirements as job_requirements rows; retire the duplicate tracker model.

### #7 — Harden API contracts: response_model + shared Page[T] pagination + one collection envelope  `[high/L]`
*Theme: API contracts & scale ceilings · kind: design*

**Why:** Four high-severity contract findings combine: almost no read endpoint declares response_model, there is no real pagination (only an unbounded raw limit) on unbounded-growth feeds, the list envelope is inconsistent, and write bodies are untyped dicts. This is both a scale fix (unbounded feeds will OOM/time out) and the prerequisite for generating typed TS clients from OpenAPI (kills MSW drift), so it compounds frontend reliability too.

**First steps:** Define a shared Page[T]{items,total,next_cursor} + PageParams and apply keyset pagination to activity/coherence/jobs/mcp-stats; set response_model on the highest-traffic resources (universe entities, documents, jobs, snapshot); add request models for core mutations; then generate the TS client via openapi-typescript.

### #8 — Light up the worker tier and wire migrations into deploy  `[high/M]`
*Theme: Observability, reliability & CI honesty · kind: ops*

**Why:** The entire background tier (syncs, renders, reminders, enrichment) initializes neither Sentry nor OTel, exposes no metrics, and has no container healthcheck — a wedged worker silently stops all background work while the API stays green. Combined with no migration step in deploy (schema upgrades are manual and unobservable), this is the reliability blind spot that will cause the quietest, longest outages. Required before the outbox worker (theme 4) and re-sync crons (theme 9) can be trusted.

**First steps:** Call init_sentry()/init_otel() in worker.startup(); stand up a worker metrics exporter and a Redis-heartbeat healthcheck with queue-depth/oldest-job alerts; add a gated 'alembic upgrade head' release step that refuses to serve when the DB revision is behind head.

### #9 — Make background tasks fail loudly and retry; add HTTP RED metrics  `[high/M]`
*Theme: Observability, reliability & CI honesty · kind: design*

**Why:** Background tasks swallow exceptions and return {ok:False}, so arq marks them successful and nothing retries — silent data loss across syncs/enrichment/email, and a direct no-silent-errors violation. Pairs with the absence of any request rate/latency/status metrics. Small-to-medium effort, large reliability and visibility payoff, and it makes the outbox worker safe to ship.

**First steps:** Classify failures: raise arq.Retry(defer=backoff) with max_tries on transient errors, capture terminal errors to Sentry + a failure metric + a visible failed state; add a metrics middleware emitting cvs_http_requests_total and cvs_http_request_duration_seconds keyed on the matched route template.

### #10 — Add a periodic GitHub/LinkedIn re-sync engine feeding a durable review queue  `[high/M]`
*Theme: Onboarding, activation & retention loops · kind: missing_feature*

**Why:** The product's core promise — 'your universe grows over time' — has no engine: there is no scheduled re-sync, and suggestions/enrichment never become a countable, returnable retention mechanic. This is the primary retention loop and depends on themes 3 (activation state) and 8/9 (reliable worker). Two findings (re-sync cron + review queue) combine into one compounding loop.

**First steps:** Add a weekly per-connection sync cron reusing run_github_sync_task/run_linkedin_dma_sync_task fanned out like reminders_cron; route results through the coherence/enrichment engine into a persistent Review queue with a Home badge count; gate by activation/connection state.

### #11 — Enforce tenant scoping on Text2Cypher/graph reads by bound parameter, not by trusting the model  `[high/M]`
*Theme: Tenant isolation & security correctness · kind: security*

**Why:** Generated Cypher trusts the LLM to scope to the user instead of enforcing it server-side — a prompt-injection or model slip reads another tenant's graph. With AGE edges also lacking DB-level type/uniqueness constraints, the graph layer is the weakest isolation boundary. Best done right after AGE-in-CI (theme 5) so the fix is testable.

**First steps:** Parameterize user_id server-side and wrap every generated query in a fixed user-bound subquery the executor controls; validate the parsed query against an ontology-derived allowlist; centralize all edge writes through one helper that validates edge_type against the ontology enum.

### #12 — Add ATS-readiness re-parse of the generated CV plus more ATS-safe templates  `[high/M]`
*Theme: End-to-end job-seeker funnel completeness · kind: missing_feature*

**Why:** The CV deliverable has templates but never re-parses the GENERATED document against the target JD — this is the Rezi/Jobscan headline feature and the most defensible 'why this tool' value-add the product is missing. Directly increases perceived deliverable quality and is a natural premium/Pro differentiator, reinforcing the monetization fix in rank 1.

**First steps:** Add an ATS-readiness score that re-parses the rendered CV for keyword coverage vs the JD, risky formatting, and completeness; surface a live score on the generate page; ship 2-3 additional ATS-safe templates with a picker.

### #13 — Consolidate the 26-specialist team into a few real specialists + a typed entity-curator  `[high/L]`
*Theme: Agentic system efficiency & correctness · kind: design*

**Why:** ≈17 of 26 specialists are near-identical entity-CRUD agents that inflate route-mode latency, token cost, and misroute rate, while domain_templates.py bloats every prompt and model tiers are cosmetic. Collapsing them cuts per-turn cost and latency materially and reduces routing errors — compounding with prompt caching (rank 14). Large but high-leverage for unit economics.

**First steps:** Collapse entity agents into 1-2 'entity curator' specialists backed by one propose_entity(entity_type enum) tool; keep only genuinely distinct reasoning specialists (cv_coach, job_strategist, interview_prep, insights); make tiers real and few (NANO for capture/routing, PREMIUM for reasoning); move shared boilerplate into a cached prefix.

### #14 — Add prompt caching breakpoints on the stable system/schema prefix  `[high/M]`
*Theme: Agentic system efficiency & correctness · kind: performance*

**Why:** A large, stable system+roster+schema prefix is re-sent uncached on every turn. Anthropic ephemeral cache_control breakpoints cut input token cost dramatically on a chat-heavy product where cost-per-turn directly determines margin. Low risk, fast payback, and it pairs naturally with the specialist/template consolidation in rank 13.

**First steps:** Insert cache_control: ephemeral at the end of the stable prefix in factory model construction/anthropic_sanitize; order messages so volatile content (user turn, retrieved snippets) follows the cached prefix; verify cache-hit token accounting in the existing llm_tracking.

### #15 — Move per-turn enrichment off the hot path and gate graph re-mirroring by change-log  `[high/M]`
*Theme: Agentic system efficiency & correctness · kind: performance*

**Why:** Every message triggers turn-LLM + Agno memory consolidation + full-graph async enrichment + an overlapping sliding-window digest, and post-run enrichment re-mirrors EVERY entity into AGE on every turn. This is the dominant per-turn cost/latency multiplier and a Postgres-connection amplifier against the 15-connection pool. Depends on the outbox/change-log (theme 4) to gate by dirty entities.

**First steps:** Make enrichment incremental off change_log (mirror only entities changed since last run) with a per-user dirty flag + debounce; consolidate memory every N turns or at session close; resolve the factory.py:500 TODO so only one memory layer runs; single-flight the post-run digest.

### #16 — Persist interview-prep and search-strategy as reusable artifacts, not ephemeral chat  `[medium/M]`
*Theme: End-to-end job-seeker funnel completeness · kind: missing_feature*

**Why:** Interview prep and search strategy are ephemeral chat whose only durable output is a freeform note — the active-search specialists produce nothing durable or actionable. Persisting per-application prep artifacts and a search-strategy/weekly-target plan rebalances the roster toward execution and gives the tracker (rank 6) real content to surface. Builds directly on the first-class application pipeline.

**First steps:** Persist per-application artifacts: a company/role research brief, a versioned competency question bank, STAR drafts pulled from the graph, mock-interview transcripts with scoring, and a prep checklist; give active-search specialists tools that write a search-strategy plan and a per-application action queue surfaced in the tracker/dashboard.

### #17 — Add browser-extension job capture + ESCO-graph role recommendations  `[high/L]`
*Theme: End-to-end job-seeker funnel completeness · kind: missing_feature*

**Why:** The funnel only opens at 'paste a JD' — there is no role discovery or job ingestion, which is the exact Teal/Huntr acquisition wedge. A 'save this job' capture plus personalized recommendations from the ESCO graph + embeddings already present turns the product from a tool you remember to open into a daily habit. High impact but larger surface (extension), so it follows the pipeline and tracker foundations.

**First steps:** Ship a lightweight browser-extension 'save this job' that creates a Saved application via the new pipeline API; add personalized role recommendations from the ESCO occupation graph + existing embeddings on Home; optionally add a board/ATS feed ingestion as a follow-up.

### #18 — Close the skill-gap loop into a tracked, auto-re-scored upskilling plan  `[medium/M]`
*Theme: End-to-end job-seeker funnel completeness · kind: design*

**Why:** Skill-gap detection produces gaps but never a tracked plan, so the insight evaporates. Auto-generating a persisted skill-gap plan as goals with progress that re-scores as items complete creates a measurable improvement loop — a retention and value driver that reuses existing specialists and match-scoring. Depends on the pipeline/target-role data from rank 6.

**First steps:** When match-scoring finds gaps for a target role, auto-generate a skill-gap plan (specific courses/certs via existing specialists) persisted as goals with progress; re-score the match automatically as items are completed and surface deltas on the dashboard.

### #19 — Add lifecycle emails (Day-1 finish-setup, weekly new-signals digest)  `[medium/M]`
*Theme: Onboarding, activation & retention loops · kind: missing_feature*

**Why:** Only reminders reach the user by email; the richer finish-setup/new-signals/suggestions nudges never leave the app, so re-engagement depends on the user remembering to return. Lifecycle email is the cheapest retention multiplier once server activation state (rank 3) and the re-sync/review queue (rank 10) exist — which is precisely why it is sequenced after them.

**First steps:** On the existing email infra, add a Day-1 'finish setup' for empty-universe users and a weekly 'N new signals / N suggestions to confirm' driven off the review queue and re-syncs, gated by the server activation state and a per-user email-frequency preference.

### #20 — Make GDPR deletion/export complete and credential-revoking  `[medium/M]`
*Theme: Tenant isolation & security correctness · kind: missing_feature*

**Why:** Account deletion is soft-delete only (no erasure, no OAuth/MCP token or BYOK key revocation) and the Art. 20 export omits ~20 user-scoped tables while silently embedding per-table errors in a 200. This is a genuine compliance and security-hygiene gap for an EU product handling sensitive career data; medium effort but legally non-negotiable before scale, and it reuses the dynamic-table-set pattern that also benefits the eraser.

**First steps:** Make deletion two-phase: immediate revoke of all credentials (refresh + OAuth via OAuthStore.revoke_all_for_user + BYOK delete + external_account disconnect) then a scheduled hard-erase; derive the export set dynamically from information_schema (tables with user_id ∪ {users}) via one shared registry consumed by migrations, exporter, and eraser; add a CI test that fails when a user-scoped table is missing from the set.
