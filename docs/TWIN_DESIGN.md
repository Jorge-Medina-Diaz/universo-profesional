# Public Digital Twin — architecture & requirements (design doc)

> Status: **DESIGN ONLY** (approved scope of the 2026-06 transformation plan,
> phase 4). No public endpoints exist yet; the only groundwork shipped is the
> `public_profiles` table (migration 0040) so later phases need no schema
> dance. Implementation is a future cycle, after the GenUI + proactive-loop
> phases land.

## 1. Product framing

**What it is:** a recruiter (or anyone with the link) chats with a read-only
agent that answers questions about a user's professional universe —
experience, projects, skills with evidence, preferences the owner chose to
expose. The same surface doubles as the user's public portfolio page.

**Positioning (market-research-informed):** there is NO demonstrated demand
yet for "chat with a candidate's clone" (Delphi et al. target creators;
recruiter AI spend goes to recruiter-side tooling). Frame it as **async
recruiter engagement on an evidence-grounded profile**:

- "Mi twin responde mientras yo trabajo" — passive candidates stop losing
  opportunities to slow replies.
- Every answer is grounded in the knowledge graph (entity citations), not a
  personality imitation — the differentiator vs. content-trained clones.
- The page is a portfolio first (SEO-visible, embed-able); the chat is the
  hook. If recruiter-side chat adoption disappoints, the surface still earns
  its keep as the best portfolio in the market.

**Non-goals:** writing anything to the universe from the public surface;
recruiter accounts/marketplace (deferred until demand is proven); voice.

## 2. Requirements

### Owner (the user)
- R-O1 Enable/disable the public profile; revocable slug (`/p/{slug}`).
- R-O2 Curation: default-deny visibility — per entity-kind toggles AND
  per-entity overrides; redaction options (hide employers' names, coarse
  dates "2019-2021" → "~3 años", hide salary/preferences entirely).
- R-O3 Persona boundaries: a short owner-editable "what the twin may say"
  charter (e.g. "no salary talk; redirect to a call").
- R-O4 Analytics: questions asked, entities viewed, visit counts, referrer;
  "recruiters keep asking about X — add evidence for it" feeds the nudge
  engine (phase 3 synergy).
- R-O5 Pro-tier gate; free tier gets the static portfolio page only.

### Visitor (recruiter)
- R-V1 No account; instant chat; suggested questions seeded from the
  profile ("¿Cuál fue su mayor proyecto cloud?").
- R-V2 Grounded answers with inline citations that deep-link to profile
  sections; "I don't know / not shared" over speculation — ALWAYS.
- R-V3 Handoff: "agenda una llamada / deja tu contacto" card → owner gets a
  lead notification (the conversion moment).

### Platform
- R-P1 Abuse: per-IP and per-slug rate limits; max turns/session; daily
  token budget per profile (owner-visible); CAPTCHA after N anonymous
  sessions/day; prompt-injection guardrail (reuse `PromptInjectionGuardrail`).
- R-P2 Cost: Haiku-only; semantic cache over recruiter FAQs (research shows
  60–90% hit rates on FAQ-shaped traffic); profile context as a stable
  1h-TTL cached prompt prefix.
- R-P3 Privacy: PII redaction pass on output (email/phone never leave);
  GDPR — visitor transcripts are owner data (export/erase with the account).
- R-P4 Zero blast radius on the authenticated app (separate team factory,
  separate session namespace, read-only DB role).

## 3. Architecture

### 3.1 `public_profile` bounded context (`backend/src/public_profile/`)

- **PublicProfile** — `user_id (PK→users)`, `slug UNIQUE`, `enabled`,
  `curation jsonb` (kind toggles, per-entity overrides, redaction flags,
  charter text), timestamps. *(Table shipped in migration 0040.)*
- **TwinSession** — `id`, `profile_user_id`, `visitor_fingerprint`
  (IP-hash + UA-hash), `started_at`, `turns`, `tokens_spent`.
- **VisitorQuestion** — `session_id`, `question`, `answer_summary`,
  `entities_cited uuid[]`, `unanswerable bool`, `created_at`. Feeds R-O4 and
  the phase-3 nudge engine (`signal_gap` candidates).
- **Lead** — `profile_user_id`, `contact`, `message`, `created_at` (R-V3).

### 3.2 Read path & scoping

- Visibility resolution = `curation` applied at the **retrieval layer**: a
  `PublicScopeFilter` wraps `hybrid_retrieve(user_id=owner, scope=public)`
  so invisible entities never reach the model (not prompt-level filtering).
- Dedicated Postgres role `cvs_twin` (SELECT-only on the user tables +
  graph schemas) — even a compromised public runtime cannot write.
- RLS: requests run with `app.current_user_id = owner_id` (read scope);
  the role's lack of INSERT/UPDATE/DELETE is the second wall.

### 3.3 Public team factory (`build_public_twin_team`)

Mirror of `factory.py` patterns, but:
- Single agent (no routing — latency + cost), Claude Haiku, temp 0.3.
- Tools: `universe_retrieve` (public-scoped), `get_career_pillars`,
  `explain_path`, `present_*` insight cards (trajectory/experience/project),
  `suggest_followup_questions`, `offer_contact_card`. NO propose_*, NO
  writes, NO `search_knowledge` over private docs unless curated in.
- `enable_user_memories=False`, `enable_session_summaries=False`; session
  namespace `twin-{slug}-{session_id}` in the agno DB (never `main-<uid>`).
- System prompt = profile digest (stable, cache_control 1h TTL) + charter +
  grounding doctrine ("cite entity ids; refuse what isn't shared").

### 3.4 Transport & frontend

- Reuse the AG-UI SSE bridge with a `public=true` mode: separate router
  `/twin/{slug}/run` (no JWT; TwinSession cookie), same event pipeline
  (cleaner, metrics) minus proposal injection.
- Public page is a **separate SSR/static route** (the SPA is hash-routed and
  invisible to crawlers): prerendered profile (JSON-LD `Person`, OpenGraph,
  llms.txt entry) + an embedded chat island reusing CopilotKit components
  + a read-only `GraphView` (ambient mode, no inspector).
- Embeddable widget (iframe) and vanity domains: phase 2 of the build, after
  core demand validation.

### 3.5 Reuse map (exists today → twin use)

| Existing module | Reuse |
|---|---|
| `graph/application/retrieval/*` | retrieval as-is + `PublicScopeFilter` |
| `agents/factory.py` patterns + `PromptInjectionGuardrail` | public team factory |
| `agents/interfaces/agui_*` pipeline stages | public SSE route (minus proposals) |
| `shared/rate_limit.py` | per-IP/per-slug limits (share-endpoint precedent) |
| `documents` share-token plumbing (`P0.4`-hardened) | slug/token validation patterns |
| `frontend/src/graph/GraphView.tsx` | ambient read-only constellation |
| `frontend/src/pages/SharePage.tsx` | public page skeleton |
| `chat/cards` insight components | grounded answer cards |
| reminders/email infra | lead + weekly-views notifications |
| `llm_tracking` | per-profile token budgets (R-P2) |

## 4. Sequencing estimate (when implementation is greenlit)

1. **Static public profile** (~1.5 wk): context + curation API + SSR page +
   SEO. Validates the portfolio half alone.
2. **Twin chat** (~2 wk): public team factory, public SSE route, abuse
   controls, semantic cache, owner analytics.
3. **Conversion & growth** (~1 wk): lead card, weekly-views email, embed
   widget, "claim your twin" CTA in onboarding.

## 5. Open questions (decide before building)

- Slug namespace: global (`/p/jorge`) vs per-tenant random (unguessable) —
  recommendation: random by default, vanity as Pro upsell.
- Semantic-cache invalidation on profile edits (coherence change_log hook).
- Whether VisitorQuestion retention needs a TTL (privacy vs analytics).
- EU AI Act disclosure copy ("estás hablando con un agente de IA").
