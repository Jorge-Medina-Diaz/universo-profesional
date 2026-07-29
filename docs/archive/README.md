# Archive

Point-in-time records. Kept because they show how the system got here — the
original spec, the audits that drove the remediation passes, the research that
shaped the graph design.

**Do not treat any of this as current.** Several files describe a 24/26/28-agent
team (the code runs **7**) and a 3-lane retriever (it runs **5** plus a rerank
stage). Where a claim here disagrees with the [README](../../README.md) or the
[docs index](../README.md), those win.

| File | Date | Why it's here | Superseded by |
|---|---|---|---|
| [README-dev-es.md](README-dev-es.md) | 2026-06 | The original Spanish developer README. Still a good local-setup walkthrough, but its stack line was wrong (claimed Tailwind 4 + shadcn/ui + TanStack Router; actually Tailwind 3.4, in-house primitives, hand-rolled hash router). | [README.md](../../README.md) + [LOCAL_DEPLOY.md](../LOCAL_DEPLOY.md) |
| [PLAN.md](PLAN.md) | 2026-06-09 | The founding technical spec and market analysis. Self-marked `[HISTÓRICO]`. Origin of the wrong stack claims and of an `ai_generation/` bounded context that was never built. | [AGENTS.md](../../AGENTS.md) |
| [PRODUCT_ROADMAP.md](PRODUCT_ROADMAP.md) | 2026-06 | 12-lens principal-level product audit, 20 items. Item #13 was "consolidate the 26-specialist team" — that shipped. | — (closed) |
| [PRODUCT_ROADMAP_PROGRESS.md](PRODUCT_ROADMAP_PROGRESS.md) | 2026-06 | Progress log for the above. Closed. | — |
| [AUDIT_REMEDIATION_FOLLOWUP.md](AUDIT_REMEDIATION_FOLLOWUP.md) | 2026-06 | Deferred medium/low-severity items from the full-stack audit. | — |
| [LEGACY_AUDIT_2026-05-27.md](LEGACY_AUDIT_2026-05-27.md) | 2026-05-27 | Multi-agent legacy / tech-debt audit. Findings remediated. | — |
| [LANDING_DOSSIER.md](LANDING_DOSSIER.md) | 2026-06 | Product narrative and positioning for the landing redesign. Claims "28 especialistas" and "RAG híbrido de 3 carriles" — both wrong now. | The landing copy deck in `frontend/src/landing/i18n.ts` |
| [agent-flow.md](agent-flow.md) | 2026-05-19 | End-to-end message path. The narrative still holds; the file map at the end is wrong on five paths (`specialists/` count, `sliding_window.py`, `session_digest.py`, `actions.tsx`, `UniverseDrawer.tsx` — all deleted or moved). | [agents/tools.md](../agents/tools.md) |
| [architecture.md](architecture.md) | Sprint R | The "reasoner with intelligent persistence" coordinator vision. Enumerates 28 named specialist agents, none of which exist — they were merged into `entity_curator` / `profile_analyst` / `domain_expert`. | `backend/src/agents/factory.py` |
| [agno-migration.md](agno-migration.md) | 2026-05 | Record of the Node `copilotkit-runtime` → Agno AG-UI migration. Completed; the Node container is gone. | — |
| [linkedin-dma-application.md](linkedin-dma-application.md) | 2026-06 | Walkthrough for the LinkedIn DMA data-access application. Self-marked `PAUSADO`. | [bright-data-setup.md](../integrations/bright-data-setup.md) |
| [RAG-CV-market-research-2026.md](RAG-CV-market-research-2026.md) | 2026-05-26 | Competitive and RAG-landscape research. Describes a "24-agent team" and 3-lane retrieval. | — |
| [agentic-deep-dive/](agentic-deep-dive/) | 2026-05 | `RESEARCH_INFORM.md` (research input) and `RFC_UNIVERSO_PROFESIONAL_V2.md` (draft RFC for the knowledge/agent subsystem). The RFC's "refactor to 4 specialised agents" was superseded by the 26 → 7 consolidation. | [architecture/graph-rag.md](../architecture/graph-rag.md) |
