# 4-layer memory architecture

Each layer has a different shape, lifecycle, and consumer. The coordinator
agent decides which layer (or layers) a given user utterance lands in.

## L1 — Universe entities (structured, current snapshot)

| | |
|---|---|
| **What** | 9 entity types: educations, experiences, projects, skills, certifications, courses, languages, achievements, interests |
| **Storage** | One PG table per entity (`educations`, …) with embedding column |
| **Mutability** | Through the **Coherence Engine** (`upsert_*`). Direct CRUD also exists but bypasses merge — discouraged for the agent path. |
| **Read primary** | `GetUniverseSummary` (counts, headline, top skills, recent items) |
| **Used by** | CV generation, MCP tools, UI tables, semantic search |

If a fact fits one of the 9 buckets, it goes here. Schema constraints +
merge rules keep it clean.

## L2 — Notes (semi-structured narrative)

| | |
|---|---|
| **What** | Free-form markdown + tags. Not tied to an entity (but can be evidence-linked). |
| **Storage** | `notes` table with embedding |
| **Mutability** | `CreateNote` / `UpdateNote` use cases, reached from the agent via the `add_note` / `update_note` tools (owned by `entity_curator`; `job_strategist` also carries `add_note`) or via REST `/api/v1/notes` |
| **Read primary** | `ListNotes(tags=...)` |
| **Used by** | CV generation ("currently learning" section), curator ("you wrote a note about X in May; still relevant?"), the user via `/notes` page |

When the user says "estas semanas he estado investigando RAG", `entity_curator`
calls `add_note` and writes a note tagged `rag, learning, reading-thread-2026-05`.
A month later, a follow-up note on the same topic is appended (or merged via
`update_note`). The agent can `list_notes(tag='rag')` to surface the thread.

## L3 — Agno memories (atomic facts)

| | |
|---|---|
| **What** | Single-sentence facts about the user that don't fit any entity. |
| **Storage** | `agno_memories` (managed by Agno's `MemoryManager`) |
| **Mutability** | Automatic: the team runs with `enable_user_memories=True` + `update_memory_on_run=True` (one consolidation pass after each turn). `enable_agentic_memory` is deliberately `False` — it fires a nested LLM call on *every* memory op. |
| **Read primary** | Agno injects relevant memories into every run's context automatically. |
| **Used by** | The agent itself ("the user is vegetarian", "prefers async") |

Examples: "prefiere trabajo remoto", "no tolera oficinas ruidosas",
"actualmente investigando RAG (mayo 2026)". These shape tone and routing
decisions but never appear on a CV.

## L4 — Knowledge (unstructured documents)

| | |
|---|---|
| **What** | Long-form content the user uploads: CV PDFs, papers, exports |
| **Storage** | `agno_knowledge_chunks` (PgVector + metadata) |
| **Mutability** | `ingest_document(file_id, tags)` queues parsing → chunk → embed → insert; updates via `Knowledge.patch_content`. |
| **Read primary** | `search_knowledge(query, top_k, tags)` — RAG retrieval |
| **Used by** | The agent when the user asks domain questions ("what papers did I read about RAG?") |

Sprint 4 wires the table but ingestion runs as a follow-up. The existing PDF
CV parser still extracts into universe entities directly (L1); it will gain
a "store original in knowledge too" branch in Sprint 5.

## Decision tree (coordinator)

```
user utterance arrives
│
├─ fits a universe entity? (job, degree, skill, project, …)
│    yes → route to the matching specialist → propose + upsert (L1)
│           if the skill came from a project/job/course also mentioned,
│           pass derived_from_*_id so the engine auto-links L1↔L1 evidence
│
├─ narrative biography? (learning thread, opinion, ongoing context)
│    yes → entity_curator → add_note (L2)
│
├─ atomic preference or context? ("prefiero remoto", "vegetariano")
│    yes → Agno's enable_user_memories + update_memory_on_run captures
│          it in one pass after the turn (L3)
│
└─ user uploaded a long document?
     yes → ingest_document → chunk + index in Knowledge (L4, planned)
```

Same utterance can hit multiple layers. The classic example from the plan:

> "Estas semanas he estado investigando arquitecturas RAG, leí estos 3 papers
> e hice un demo con LlamaIndex."

→ L1: `project(demo)`, `skill(LlamaIndex, derived_from=demo)`, `skill(RAG)`,
  `interest(RAG)`.
→ L2: `note(body="…investigando RAG…", tags=[rag, papers, learning-thread-2026-05])`.
→ L3: Agno memorizes "currently learning RAG (May 2026)".
→ L4: when the user uploads the 3 PDFs, chunks indexed with `tags=[rag, paper]`.

Six months later when asked "what papers did I read about RAG?" the agent
combines L4 retrieval (paper titles) + L2 (the user's notes about them) +
L1.change_log (timeline of when interest grew).

## Why not collapse layers?

- **L1 → L2**: structured CV fields can't hold opinions or contexts.
- **L2 → L3**: notes are user-authored; memories are agent-derived. Mixing
  them confuses provenance and editing.
- **L3 → L1**: atomic facts ("vegetariano") don't belong on a CV; promoting
  them to entities would clutter the universe.
- **L4 → L2**: papers/exports are big and indexable; storing them in
  `notes` blows up that table and loses the chunking-for-RAG primitive.

Each layer is tuned to a specific access pattern. Coordinator orchestration
+ Coherence Engine cross-link them where it matters.
