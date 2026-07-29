# Coherence Engine

The piece that distinguishes this system from "CRUD with a chatbot on top".
Sits between every write path (agent tool, REST API, batch import) and the
universe tables: searches first, decides merge-vs-create by declarative rules,
records every field-level change, and links evidence to build the universe
graph.

## Why

Without coherence, the system accumulates duplicates and contradictions. The
user mentions Python today → skill row #1. Six months later they mention "5
years Python" → row #2. A year later "expert in Python" → row #3. CVs become
noisy, suggestions wrong, knowledge graph useless.

The engine is the answer: every write is an **upsert** with rules — never a
blind append.

## Where it lives

```
backend/src/coherence/
├── domain/
│   ├── upsert_decision.py   # MatchResult, MergePlan, UpsertOutcome
│   ├── merge_rules.py       # one pure function per entity
│   └── er_rules.py          # ErConfig: blocking + thresholds per kind
├── application/
│   ├── upsert_use_cases.py  # UpsertUniverseEntity orchestrator
│   ├── change_log.py        # append-only writer helpers
│   ├── coherence_v2.py      # ESCO linking + edge materialisation post-upsert
│   ├── entity_resolution.py # EntityResolutionPipeline (blocking → pairwise → clusters)
│   └── ports.py             # ChangeLogRepository, SemanticMatcher
├── infrastructure/
│   ├── orm.py                # UniverseChangeLogOrm
│   ├── change_log_repo.py
│   └── semantic_matcher.py   # PgVectorSemanticMatcher
└── interfaces/api/router.py  # /api/v1/coherence/{upsert,changes,review-queue}
```

## The orchestrator

`UpsertUniverseEntity.execute(entity_type, user_id, payload, uow, source)`:

1. **Find existing**:
   - Exact match on the canonical name field
     (`name`/`organization`/`title`/`institution`/`code`).
   - Else, semantic similarity via `PgVectorSemanticMatcher.find_most_similar`
     with the entity's embedding text:
     - `score ≥ AUTO_MERGE_THRESHOLD (0.92)` → silent merge.
     - `AMBIGUOUS_LOW (0.80) ≤ score < 0.92` → emit a suggestion, return
       `status="suggested"` without mutating.
     - `score < 0.80` → no match.
2. **Create** (no match): call `*Crud.add` via the existing CRUD path,
   record `change_log` with `change_type="create"`, link evidence if skill +
   `derived_from_*_id`.
3. **Merge** (match): run `merge_rules.merge_for(...)`. If the plan
   `needs_user_confirmation` → emit suggestion. Else call `*Crud.update`
   with `merged_payload` and record one `change_log` row per field diff.

## Merge rules per entity

| Entity | Match by | Merge highlights |
|---|---|---|
| **skill** | name (case-insensitive) | `years = max`, `level = max-rank(basic→expert)`, `last_used_year = max`, `evidence_refs = union`. **`category` conflict ⇒ suggestion** (default rejects soft-vs-hard auto-changes). |
| **experience** | organization (then semantic) | `end_date = max`, `is_current = false` if `end_date` set, `highlights ∪`, `competences ∪`. |
| **education** | institution | `degree`/`field_of_study` prefer existing when set; missing → take new. `highlights ∪`. |
| **project** | name | `tech_stack ∪`, `highlights ∪`, `status = new` (most recent wins), `description`/`impact` prefer existing. |
| **certification** | name | `expires_on = max`, other fields prefer existing. |
| **course** | title | **`completed_on` immutable once set** (never overwrite a completion date). `duration_hours = max`. |
| **language** | code (ISO-639-1) | `level = max(CEFR)`. |
| **achievement** | title | `description`/`context` prefer existing; everything else additive. |
| **interest** | name | `description` concatenates new content if not already present. |

Each rule is a **pure function**: `(existing, payload) → MergePlan`. No IO,
no DB, easy unit tests (see `tests/unit/test_merge_rules.py`).

## Auto-evidence

When a skill upsert payload carries `derived_from_project_id=<id>` —
or any other `derived_from_<entity>_id` — `coherence_v2._materialise_edges`
writes a typed `DERIVED_FROM` edge from the skill to that source in the
`universe_personal` graph. Idempotent: edge writes go through
`UniverseGraphService.upsert_edge`, which uses Cypher `MERGE`, so restating
the same relation never duplicates it. (The legacy `evidences` table was
dropped in migration 0017 — evidence lives in the graph now.)

Result: the user's Python skill ends up linked to `project-ml-demo`,
`experience-anthropic`, and `course-rag-101`. The CV generator can rank
skills by evidence-edge count = real depth.

## Change log (trajectory)

`universe_change_log` is **append-only**. Every `update` writes one row per
field changed:

```
id | user_id | entity_type | entity_id | change_type | field | old_value | new_value | reason | source | agent_run_id | changed_at
```

Queries the system does against it:

- "When did Python go from intermediate to expert?" — `list_for_entity(entity_type='skill', entity_id=...)`.
- "What's been touched in the last week?" — `list_for_user(since=...)`.
- "Show me the recent learning thread" — filter by `source='agent_chat' AND reason ILIKE 'upsert%' AND entity_type IN ('skill','interest')`.

See [data-evolution.md](../architecture/data-evolution.md) for queries.

## REST surface

- `POST /api/v1/coherence/upsert` — body `{entity_type, payload, source}`.
  Used by the frontend's confirmation cards. Response: `{status, entity_id,
  diffs, suggestion_id, reason}`.
- `GET /api/v1/coherence/changes?limit=&entity_type=&entity_id=` — feed for
  the "Trayectoria" tab in the Universe drawer.

## Agent tools that exercise the engine

- `find_existing(entity_type, query)` — for the agent to check before
  proposing.
- `propose_merge_suggestion(entity_type, candidate_ids)` — open a suggestion
  when the agent itself detects two entries that look the same.
- `mark_stale(entity_type, entity_id)` — drop `confidence` to 0.3 without
  deleting; flips into the curator's "consider archiving" filter.
- `get_change_history(entity_type, entity_id)` — read access for the
  agent to ground "when did you change X?" answers.

## Tradeoffs

- **Threshold tuning**: 0.92 / 0.80 are heuristics. Watch the `suggestions`
  table — if users keep rejecting auto-merges, raise to 0.95. If too many
  things slip through as new, lower to 0.88.
- **Embedding stability**: switching from `deterministic` (dev) to OpenAI
  vectors changes scores. Re-embed all entities before turning on the new
  provider in prod.
- **Pure rules** don't handle every edge case. When `needs_user_confirmation`
  fires (e.g., skill category conflict), the engine never auto-decides — it
  always asks. Conservative by design.
