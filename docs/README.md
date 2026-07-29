# Documentation

Organised by what you're trying to do, not by directory. Everything under
[`archive/`](archive/) is a point-in-time record kept for provenance — it
describes the system as it *was*, not as it is.

Most docs are in Spanish (the product's language); the operations and
architecture notes are mixed Spanish/English.

## Start here

| Doc | What it answers |
|---|---|
| [../AGENTS.md](../AGENTS.md) | Repo map, bounded contexts, build/test/lint commands, conventions. The single onboarding doc. |
| [LOCAL_DEPLOY.md](LOCAL_DEPLOY.md) | Run the whole stack locally, plus the mock → real provider matrix. |
| [../DESIGN.md](../DESIGN.md) | The design system: tokens, type scale, motion, do's and don'ts. |

## How the product works

| Doc | What it answers |
|---|---|
| [agents/coherence-engine.md](agents/coherence-engine.md) | Why writes merge instead of accumulating. **The differentiator — read this first.** |
| [architecture/graph-rag.md](architecture/graph-rag.md) | Personal hypergraph (Apache AGE) + ESCO ontology + the 5-lane hybrid retriever. |
| [architecture/memory-layers.md](architecture/memory-layers.md) | The four memory layers and what lands in each. |
| [architecture/data-evolution.md](architecture/data-evolution.md) | `universe_change_log` + the evidence graph: history without loss. |
| [agents/single-chat.md](agents/single-chat.md) | One persistent thread per user, and how context stays bounded. |
| [agents/tools.md](agents/tools.md) | The agent tool catalogue, including the generative-UI (HITL) cards. |
| [TWIN_DESIGN.md](TWIN_DESIGN.md) | The public digital twin (`/t/{slug}`) and its embed widget. |

## Integrations

| Doc | What it answers |
|---|---|
| [integrations/MCP_TOOLS.md](integrations/MCP_TOOLS.md) | The remote MCP server: OAuth 2.1 + PKCE + DCR, and the tool surface. |
| [integrations/bright-data-setup.md](integrations/bright-data-setup.md) | LinkedIn data sourcing: why Bright Data, and the alternatives considered. |

## Running it in production

| Doc | What it answers |
|---|---|
| [OPERATIONS/DEPLOYMENT.md](OPERATIONS/DEPLOYMENT.md) | Fly.io (default) and VPS Docker. |
| [OPERATIONS/DEPLOY.md](OPERATIONS/DEPLOY.md) | The prod-flavoured stack on your own machine. |
| [OPERATIONS/MIGRATIONS.md](OPERATIONS/MIGRATIONS.md) · [BACKUP_RESTORE.md](OPERATIONS/BACKUP_RESTORE.md) · [ROLLBACK_RUNBOOK.md](OPERATIONS/ROLLBACK_RUNBOOK.md) | Schema, data, and undo. |
| [OPERATIONS/MONITORING.md](OPERATIONS/MONITORING.md) · [INCIDENT_RUNBOOKS.md](OPERATIONS/INCIDENT_RUNBOOKS.md) | Signals worth watching, and what to do at 3am. |
| [OPERATIONS/SECRETS_ROTATION.md](OPERATIONS/SECRETS_ROTATION.md) · [COSTS.md](OPERATIONS/COSTS.md) | Rotation cadence; unit economics (as of 2026-05). |
| [OPERATIONS/LAUNCH_CHECKLIST_V1.md](OPERATIONS/LAUNCH_CHECKLIST_V1.md) · [PRODUCTION_READINESS_CHECKLIST.md](OPERATIONS/PRODUCTION_READINESS_CHECKLIST.md) | Pre-deploy gates. |

## Engineering evidence

Worth reading if you want to see how decisions were made and verified, rather
than asserted.

| Doc | What it shows |
|---|---|
| [OPERATIONS/LATENCY_BASELINE.md](OPERATIONS/LATENCY_BASELINE.md) | Chat TTFT p50 6.63s → 3.11s (−53%), with the methodology and the changes that moved it. |
| [SECURITY_RLS_STATUS.md](SECURITY_RLS_STATUS.md) | Enforcing Postgres RLS surfaced four real defect classes — including a `current_setting()::uuid` policy-poison bug. What broke and how it was fixed. |
| [OPERATIONS/SECURITY_AUDIT.md](OPERATIONS/SECURITY_AUDIT.md) | Focused audit of the JWT/auth layer and MCP OAuth validation (2026-05). |

## Archive

Superseded, closed, or point-in-time. Kept for provenance; **do not treat as
current** — several of these describe agent counts and retrieval lanes that no
longer match the code. See [archive/README.md](archive/README.md).
