# Research Report: Modern RAG, AI Agents & CV/Profile SaaS Landscape
## Gaps and Opportunities for Universo Profesional

> Date: 2026-05-26
> Scope: Competitive AI tools, advanced RAG architectures, knowledge graphs, document pipelines, structured data coherence, open-source projects, best-in-class benchmarks.
> Method: Web search + codebase analysis of Universo Profesional (master branch).

---

## Executive Summary

Universo Profesional (UP) already occupies a remarkably advanced position in this landscape. Its architecture -- a 24-agent agno team, Apache AGE personal graph + ESCO ontology backbone, hybrid retrieval (BM25 + pgvector dense + PPR with RRF), a Coherence Engine with declarative merge rules, HITL confirmation cards, and an MCP server -- is 2-3 years ahead of what most competitors ship.

However, five strategic gaps emerge from this research where UP can extend its lead:

1. Multi-modal ingestion -- competitors still rely on text-only parsers; UP can own vision-first document ingestion (ColPali-style).
2. Community-summarized GraphRAG -- Microsoft GraphRAG community reports + LightRAG dual-level retrieval could replace/supplement the current PPR-only approach.
3. Agentic RAG with reflection -- the 24 specialists are static routers; adaptive retrieval with critic modules and iterative feedback would be a leap.
4. Structured extraction at ingestion -- LLM-native structured output (JSON Schema / BAML / Instructor) can replace/supplement Affinda for cost and sovereignty.
5. Best-in-class document fidelity -- WeasyPrint is solid, but LaTeX-based rendering or headless-Chrome with Paged.js would unlock pixel-perfect ATS parsing scores.

---

## 1. How Competitors Use AI (Resume.io, Novoresume, Kickresume, Teal, Rezi)

### 1.1 Feature Matrix (2025-2026)

| Product | AI Depth | Model | Key AI Feature | What is Missing |
|---------|----------|-------|--------------|----------------|
| Kickresume | Surface | GPT-4 | Full resume gen from questionnaire; AI cover letter; resume checker | No persistent knowledge graph; no semantic matching; generic bullets reported on Trustpilot |
| Resume.io | Surface | GPT-family | Job matching + distribution; interview practice | No structured profile model; document-centric |
| Novoresume | Surface | GPT-4 | AI assistant guides optimization; resume & cover letter writer | Premium-only AI; no ontology anchoring |
| Teal HQ | Moderate | Proprietary | Resume-to-job match scoring; keyword suggestions; Chrome ext. | Kanban-first, not graph-first; AI bullets reported as generic |
| Rezi | Moderate | Proprietary | JD-aware keyword injection; ATS optimization; MCP server (OAuth 2.1 + PKCE) | Resume-centric (not universe); 9 templates; no knowledge graph |
| Reactive Resume | Moderate | -- | MCP server (SEP-1649 server-card); open-source schema v5; OAuth2 + DCR | No adaptive generation; no tracker; no semantic matching |
| Jobscan | Moderate | Proprietary | ATS detection (Workday/Greenhouse/Taleo); 91% keyword accuracy | Expensive ($49.95/mo); analysis-only, no generation |
| Enhancv | Moderate | -- | 15 ATS-tested templates (90%+ parse rate by Sovren/RChilli) | Expensive; no tracker; design-first |
| Careerflow.ai | Moderate | -- | LinkedIn-to-Resume; mock interviews; one-click optimizer | Bugs reported; inconsistent UX |

### 1.2 Key Insight: The Resume-Centric Trap

Every major competitor models the document as the primary entity, not the person. Even Rezi and Reactive Resume -- the only competitors with MCP servers -- expose list_resumes, read_resume, write_resume. The user data is fragmented across multiple resume files.

UP differentiation is structural: it models a persistent personal knowledge graph (11 entity types, ESCO-linked, evidence-tracked) from which documents are projections. This is the correct architecture. The gap is not architectural -- it is messaging and speed-to-market.

### 1.3 What Competitors Do Better (Temporarily)

- Template variety: Kickresume has 50+ templates; Enhancv has 15 ATS-tested. UP targets 8 ATS + creative templates in v1.
- MCP maturity: Reactive Resume MCP implements resources, prompts, and /.well-known/mcp/server-card.json (SEP-1649). UP MCP is tools-only so far.
- ATS parse-rate validation: Enhancv publishes 90%+ parse rates tested by Sovren and RChilli. UP has not yet published equivalent benchmarks.
- Auto-apply integrations: Simplify.jobs and Jobright.ai have Workday/Greenhouse autofill. UP explicitly avoids auto-apply (correct strategic call per PLAN.md).

---

## 2. Advanced RAG Architectures

### 2.1 The RAG Evolution Spectrum

~~~
Basic RAG (2020) -> Advanced RAG (2023) -> Modular RAG (2024) -> Agentic RAG (2025) -> GraphRAG (2024-2026)
~~~

UP currently sits at Advanced/Modular RAG with graph augmentation. The next leaps:

### 2.2 GraphRAG: Microsoft Community-Summary Approach

Microsoft GraphRAG (Edge et al., 2024) introduced a paradigm shift:

1. Indexing: Extract entities/relations from text -> build knowledge graph -> detect communities (Leiden algorithm) -> generate LLM community summaries.
2. Retrieval: For global queries, retrieve community summaries; for local queries, traverse entity neighborhoods.
3. Advantage: Answers global questions (e.g., what are the main themes in my career?) far better than vector search.

Limitation: High indexing cost; community summaries must be recomputed on insert. Academic critiques (AcademicRAG, 2025) note scalability issues for dynamic datasets.

Opportunity for UP: The personal graph is small (<10k nodes/user) and relatively static. Community summaries could be generated per user during the nightly curator run. This would power the insights_specialist and portfolio_specialist with holistic narrative generation.

### 2.3 LightRAG: Dual-Level Retrieval

LightRAG (Guo et al., 2025) replaces community reports with local + global keyword extraction:
- Local keywords: entity-specific information.
- Global keywords: broader conceptual context.
- Advantage: Lower latency, lower storage, less noise than GraphRAG.

Opportunity for UP: The current PPR retriever seeds from dense top-3. Adding LightRAG-style keyword extraction could improve retrieval for vague queries like tell me about my cloud work.

### 2.4 HippoRAG: Personalized PageRank

HippoRAG (Gutierrez et al., 2024) runs PPR over an entity graph -- UP already implements this. The gap is that HippoRAG uses a unified episodic memory graph (facts + temporal edges), whereas UP PPR runs on an igraph snapshot that is invalidated and rebuilt. The next evolution is incremental PPR updates (not full rebuilds) and bi-temporal modeling (when facts were true).

### 2.5 Agentic RAG: Reflection + Critic Modules

The Agentic RAG survey (2026) categorizes architectures:

| Dimension | UP Today | Best-in-Class Agentic RAG |
|-----------|----------|---------------------------|
| Agent Cardinality | 24 specialists (static) | Dynamic agent spawning per task |
| Control | Coordinator routes (route mode) | Hierarchical with critic/evaluator |
| Retrieval Adaptivity | Fixed 3-lane hybrid | Dynamic strategy selection per query |
| Reasoning Depth | Single-turn specialist | Multi-hop with iterative verification |

Agent-G (Agentic Graph RAG) introduces:
- Retriever Bank: modular agents for graph vs. unstructured retrieval.
- Critic Module: validates relevance/quality of retrieved info.
- Feedback Loops: iterative re-querying.

Opportunity for UP: The cv_coach or portfolio_specialist could spawn a sub-agent that iteratively retrieves, evaluates coverage, and re-queries gaps -- rather than one-shot retrieval.

### 2.6 Multi-Modal RAG for Document Ingestion

Current UP parses PDFs via pypdf + Affinda fallback. The 2026 state-of-the-art is:

| Architecture | How | Best For |
|-------------|-----|----------|
| Caption-and-index | VLM captions -> text embedding | Quick win, small corpora |
| Unified embeddings | Cohere Embed 4 / voyage-multimodal-3 | Single index, cross-modal queries |
| Page-as-image (ColPali) | Vision encoder + multi-vector retrieval | Highest recall on figure-heavy docs |
| Hybrid late-fusion | Parallel text + image indices + RRF | Most flexible, best mixed recall |

ColPali/ColQwen2 treats each page as an image, encodes patches, and retrieves via late interaction (MaxSim). No OCR, no layout detection, no table parser needed.

Opportunity for UP: Replace the current PDF import pipeline with a hybrid approach:
1. ColPali for visual retrieval of page relevance.
2. VLM (Claude Sonnet) for structured extraction of text/tables/charts from top-K pages.
3. Output feeds directly into the Coherence Engine.

This eliminates dependency on Affinda (cost + vendor risk) and handles scanned/image PDFs natively.

---

## 3. Knowledge Graph Approaches for Personal/Professional Data

### 3.1 ESCO Ontology

UP already uses ESCO (~14k skills, ~3k occupations, SKOS hierarchical, multilingual). Research confirms this is the right choice:

- LinkedIn Skills Graph (39k skills, 374k aliases) is proprietary and not reusable.
- O*NET (US DoL, 923 occupations, 177 skill elements) is US-centric and updates annually.
- WEF Global Skills Taxonomy (1,000+ core skills) is strategic but too coarse.
- ESCO is the only framework that is: official, multilingual (27 languages), free, hierarchical, and education-to-work mapped.

Gap: ESCO releases are every 2-3 years. Emerging skills (e.g., MCP server development, AI agent orchestration) will not appear for years. UP needs a custom skills overlay that captures emerging tech skills and maps them to ESCO approximations.

### 3.2 LinkedIn Approach

LinkedIn built a skills folksonomy via:
1. Discovery -> disambiguation -> deduplication pipeline.
2. Skill inference from profile connections (factor graph model).
3. Ontology moving beyond taxonomy to model rich relationships.

Lesson for UP: LinkedIn skill inference uses co-occurrence graphs (skills that appear together) and social graph signals (shared companies/titles). UP could infer skill adjacencies from the personal graph (projects that use tech X often also use tech Y) and from aggregate patterns across users (with privacy-preserving aggregation).

### 3.3 Enterprise Skills Graphs

The enterprise L&D world (Cornerstone, Degreed, Workday) builds skills graphs with:
- Canonical skills store: RDF/OWL or property graph.
- Event pipeline: Kafka/xAPI for real-time skill usage events.
- Inference services: ML for skill recommendation, prerequisite checks, proficiency scoring.

Opportunity for UP: The rubric overlay (user_rubric_signals with statuses aspire/practice/own/teach/avoid) is essentially a personal proficiency model. Extending this with prerequisite chains (e.g., to own Kubernetes, you should practice Docker) would create a personal learning pathway feature -- a unique B2C differentiator.

---

## 4. Document Generation Pipelines (PDF/DOCX) with LLMs

### 4.1 Current Landscape

| Approach | Tooling | Quality | Speed | ATS Parse Rate |
|----------|---------|---------|-------|----------------|
| HTML -> PDF (WeasyPrint) | UP choice | Good | Fast | Good |
| HTML -> PDF (Paged.js + headless Chrome) | Modern alternative | Excellent | Medium | Excellent |
| LaTeX -> PDF | ResumeFlow, academic | Excellent | Slow | Excellent |
| python-docx -> DOCX | UP choice | Good | Fast | N/A |
| Affinda API | External | 97% accuracy (vendor claim) | API latency | N/A |

### 4.2 Best Practices for LLM-Generated Documents

1. Schema-first generation: Generate JSON Resume / MAC / Europass JSON-LD first, then render. UP already does this.
2. Content preservation metric: |words(gen) n words(original)| / min(|words(gen)|, |words(original)|) -- ResumeFlow uses this to ensure the LLM does not hallucinate beyond user data. UP should implement this as a guardrail.
3. Job alignment metric: |words(gen) n words(JD)| / min(|words(gen)|, |words(JD)|) -- measure keyword overlap with the JD.
4. ATS validation layer: Parse the generated PDF with an ATS parser (e.g., Sovren, RChilli, or open-source OpenResume parser) and verify field extraction rate before presenting to user.

### 4.3 Multi-modal Document Generation

Future CVs may include:
- Portfolio pages with screenshots of projects.
- QR codes linking to live demos.
- Infographics of skill depth/evidence.

UP WeasyPrint supports CSS well, but embedding rich visuals from the graph (e.g., a sigma.js graph snapshot as an image in the CV) would be a unique feature.

---

## 5. Structured Data Extraction and Merging (The Coherence Problem)

### 5.1 The State of the Art in Entity Resolution

UP Coherence Engine is already sophisticated:
- Exact match on canonical name field.
- Semantic similarity via pgvector (thresholds: 0.92 auto-merge, 0.80-0.92 suggestion, <0.80 create).
- Pure functional merge rules per entity.
- Append-only change log.
- Auto-evidence linking.

Comparison with industry best practices (RudderStack, Data Ladder, Senzing):

| Technique | Industry Standard | UP Status |
|-----------|------------------|-----------|
| Deterministic matching (exact IDs) | First pass | Implemented |
| Probabilistic matching (fuzzy, Levenshtein, Soundex) | Second pass | Partial (cosine only) |
| ML-based matching (Random Forest, neural networks) | Advanced | Not implemented |
| Human-in-the-loop review band | 50-90% confidence | Implemented (0.80-0.92) |
| Survivorship rules (golden record) | Most recent / most complete | Implemented |
| Feedback loop (user accepts/rejects improves model) | Continuous improvement | Thresholds are static |

### 5.2 Opportunities for Improvement

1. Multi-signal matching: Combine cosine similarity + Levenshtein on normalized names + phonetic matching (Soundex/Metaphone for Spanish/English names) + ESCO URI equivalence. This would catch cases like Juan Garcia vs John Garcia or AWS vs Amazon Web Services.

2. Learned thresholds: Instead of static 0.92/0.80, track user accept/reject rates per entity type and auto-tune thresholds. E.g., if users keep rejecting auto-merges for skill, raise the threshold.

3. Cross-type deduplication via ESCO: If a course and a certification both link to the same ESCO skill URI, the system could suggest merging or flagging redundancy. UP coherence_v2.post_upsert has _attach_esco_edge() but not cross-type dedup logic yet.

4. Temporal coherence: Python (2018-2020) and Python (2022-present) should not necessarily merge -- they represent different episodes. The graph valid_from/valid_to edges handle this, but the coherence engine merge rules do not explicitly consider temporal disjointness.

---

## 6. Open-Source Projects

### 6.1 Directly Relevant Projects

| Project | What It Is | Stars / Adoption | How UP Can Leverage |
|---------|-----------|------------------|---------------------|
| Reactive Resume (rxresu.me) | Open-source resume builder, MCP server, schema v5 | Very high community | Study MCP implementation (server-card, OAuth2+DCR+PKCE) for parity |
| JSON Resume (jsonresume.org) | Standard JSON schema for resumes | De facto dev standard | UP already exports to this; study jsonresume/mcp for MCP patterns |
| Manfred MAC (getmanfred/mac) | Spanish open-source CV schema with aspirations/goals | 591 stars, 120k+ profiles | UP already plans MAC export; deepen bidirectional compatibility |
| CodeCV (codecv-co/codecv) | Modular CV as structured data (JSON/YAML/TOML) | Niche | Modular composition approach could inspire profile variants |
| Microsoft GraphRAG | Graph-based RAG with community detection | High research impact | Evaluate community summary generation for personal graphs |
| LightRAG | Simplified GraphRAG (local+global keywords) | Rising | Evaluate dual-level retrieval as PPR enhancement |
| HippoRAG | PPR over entity graphs for multi-hop QA | Academic | UP already has PPR; study bi-temporal extensions |
| ColPali / ColQwen2 | Vision-first document retrieval | Cutting-edge 2025-2026 | Replace/supplement PDF parsing pipeline |
| Graphiti (getzep/graphiti) | Real-time knowledge graphs for AI agents | Growing | Study temporal edge modeling; AGE already has valid_from/valid_to |
| DIGIMON | Modular graph-based RAG framework | Research | Reference for modular retriever design |

### 6.2 Strategic Observations

- No open-source project combines: personal knowledge graph + conversational agents + document generation + MCP + ESCO ontology. UP is building something unique.
- The closest conceptual competitor is Manfred MAC (Spanish, open, aspirational) but it is B2B2C recruiting, not B2C self-service.
- Reactive Resume is the closest technical competitor with MCP. UP should match its MCP feature surface (resources, prompts, server-card) by v1.

---

## 7. What Makes a CV/Professional Profile SaaS Best in Class

### 7.1 The 2026 Best-in-Class Checklist

Based on competitive analysis, user reviews, and architectural research:

#### A. Data Model (The Foundation)
- [x] Person-centric, not document-centric -- UP yes
- [x] Structured entity types (experience, education, skills, projects, certs, etc.) -- UP yes (11 types)
- [x] Persistent knowledge graph with typed relationships -- UP yes (Apache AGE)
- [x] Ontology anchoring for deduplication and interoperability -- UP yes (ESCO)
- [x] Evidence linking (skill demonstrated by project, job, course) -- UP yes
- [ ] Cross-type deduplication -- UP partial
- [x] Temporal validity on facts -- UP yes (graph edges have valid_from/valid_to)
- [ ] Emerging skills overlay beyond ESCO -- UP gap

#### B. AI & Retrieval
- [x] Hybrid retrieval (sparse + dense + graph) -- UP yes (BM25 + pgvector + PPR + RRF)
- [ ] Community-summarized GraphRAG for holistic queries -- UP gap
- [ ] Agentic RAG with reflection/critic -- UP gap
- [x] Multi-agent orchestration -- UP yes (coordinator + 24 specialists)
- [ ] Dynamic agent spawning (not static routing) -- UP gap
- [ ] Multi-modal ingestion (scanned PDFs, images, screenshots) -- UP gap

#### C. Conversation & UX
- [x] Conversational capture (chat, not forms) -- UP yes
- [x] Human-in-the-loop confirmation -- UP yes (HITL cards)
- [x] Streaming responses -- UP yes (AG-UI SSE)
- [x] Digest / long-term memory -- UP yes (session digest + 4-layer memory)
- [ ] Proactive suggestions (you have not updated skills in 3 months) -- UP partial (curator exists but limited proactive UX)

#### D. Document Generation
- [x] ATS-friendly templates -- UP in-progress (need parse-rate validation)
- [x] Job-description-aware tailoring -- UP yes (RAG pipeline)
- [x] Multiple export formats (PDF, DOCX, JSON Resume, Europass, MAC) -- UP yes
- [ ] ATS parse-rate validation on generated output -- UP gap
- [ ] Visual/portfolio embeds in CV -- UP gap

#### E. Ecosystem & Interoperability
- [x] MCP server -- UP yes (tools exposed)
- [ ] MCP resources + prompts + server-card -- UP gap vs. Reactive Resume
- [x] OAuth 2.1 + PKCE + DCR -- UP yes
- [x] Import from LinkedIn, GitHub, PDF -- UP yes
- [ ] Browser extension for one-click job capture -- UP gap vs. Teal, Simplify.jobs

#### F. Trust & Compliance
- [x] RGPD-native (EU hosting, encryption, right to deletion) -- UP yes
- [x] Append-only audit log -- UP yes (universe_change_log)
- [x] Confidence scores + decay -- UP yes
- [ ] Published ATS parse-rate benchmarks -- UP gap

---

## 8. Synthesis: Gaps and Opportunities

### 8.1 High-Impact, Low-Effort Wins

| Opportunity | Effort | Impact | Notes |
|-------------|--------|--------|-------|
| MCP resources + prompts + server-card | Medium | High | Match Reactive Resume MCP surface. Add universe://summary resource, prepare_application_for prompt, /.well-known/mcp/server-card.json. |
| ATS parse-rate self-check | Medium | High | After PDF generation, run open-source ATS parser (OpenResume parser or similar) and report 98% ATS-compatible to user. Publish benchmarks. |
| Learned merge thresholds | Low | Medium | Track accept/reject rates on suggestions per entity type; auto-tune 0.92/0.80 weekly. |
| Cross-type ESCO dedup | Low | Medium | If two entities link to same ESCO URI, suggest merge or flag redundancy. |
| Browser extension (job capture) | Medium | High | One-click JD capture from LinkedIn/InfoJobs. Teal and Simplify.jobs prove demand. |

### 8.2 High-Impact, High-Effort Strategic Bets

| Opportunity | Effort | Impact | Notes |
|-------------|--------|--------|-------|
| Multi-modal PDF ingestion (ColPali + VLM) | High | Very High | Eliminates Affinda dependency. Handles scanned PDFs, complex layouts, tables natively. Vision-first is the 2026 standard. |
| Community-summarized GraphRAG | High | High | Nightly curator generates Leiden communities + LLM summaries. Powers holistic insights (what are my career themes?). |
| Agentic RAG with critic modules | High | High | portfolio_specialist spawns retrieval agent -> critic agent -> synthesis agent. Iterative, verifiable, higher-quality CV generation. |
| Emerging skills overlay | Medium | High | Crowdsource/custom skills graph for AI-era skills (LLM ops, MCP development, agent design) mapped to ESCO approximations. |
| Personal learning pathways | Medium | High | Based on rubric overlay + prerequisite chains, suggest to reach Senior ML Engineer, practice X, Y, Z. Unique B2C feature. |

### 8.3 Architectural Risks to Monitor

1. Apache AGE limitations: AGE 1.5 lacks MERGE ... ON CREATE SET, has quirky parameter binding, and search_path issues. The cutover plan (Sprint R) to make AGE the source of truth is bold. Consider keeping SQL authoritative longer, or evaluate Neo4j AuraDB (managed, faster Cypher, but adds ops cost).

2. PPR cold-start: The igraph snapshot is LRU-cached (200 users). For a user with 10k+ nodes, cold snapshot loading takes 800-1500ms. As noted in graph-rag.md, persisting snapshots in Redis pickle is planned for Sprint R+. This is critical before scaling.

3. ESCO staleness: ESCO updates every 2-3 years. AI-era skills (prompt engineering, RAG architecture, MCP server development) are invisible. The custom skills overlay must be productionized before this becomes a user-visible gap.

4. MCP spec velocity: The spec is stable (2025-11-25) but extensions (Client ID Metadata, Server-Side Authorization Management) are in draft. UP abstraction of transport is correct; maintain flexibility.

5. Affinda cost: At scale, Affinda parsing could dominate per-user costs. The multi-modal VLM pipeline (ColPali + Claude extraction) is the strategic replacement but requires significant R&D.

---

## 9. Recommended Priorities (Next 3 Sprints)

### Sprint R (Current): Graph Cutover & MCP Polish
1. Complete legacy-to-graph migration (scripts/migrate_legacy_to_graph.py).
2. Add MCP resources (universe://summary, universe://experience, etc.) and prompts (prepare_application_for, quarterly_review).
3. Implement /.well-known/mcp/server-card.json (SEP-1649).
4. Persist PPR snapshots in Redis pickle for >10k node users.

### Sprint S: Retrieval Enhancement
1. Prototype community summary generation (Leiden + LLM) on 5 test-user graphs.
2. Add LightRAG-style keyword extraction as 4th retrieval lane.
3. Implement learned merge thresholds (track accept/reject rates, auto-tune).

### Sprint T: Multi-modal Ingestion MVP
1. Prototype ColPali/ColQwen2 for PDF page retrieval.
2. VLM structured extraction pipeline (Claude Sonnet with JSON Schema) from top-K pages.
3. Compare accuracy/cost vs. Affinda on 100-sample PDF test set.
4. If viable, add as progressive enhancement (Affinda primary, VLM fallback).

---

## 10. Conclusion

Universo Profesional is architecturally ahead of every competitor in the CV/professional-profile space. The combination of a personal knowledge graph, ESCO ontology, hybrid retrieval, 24-agent orchestration, Coherence Engine, and MCP server has no parallel in the market -- not in Teal, not in Rezi, not in Reactive Resume.

The strategic imperative is not to catch up but to extend the lead in three directions:

1. Retrieval intelligence: Move from PPR-only to community-summarized GraphRAG + agentic reflection.
2. Ingestion intelligence: Move from text parsers to multi-modal vision-first document understanding.
3. Ecosystem completeness: Match and exceed Reactive Resume MCP surface, add browser extension, and publish ATS benchmarks.

The window is open. Rezi and Reactive Resume have MCP but lack the graph. Manfred has the graph (MAC) but lacks the agentic interface. No one has all three. UP can be the first.

---

Report compiled from web research (May 2026) and analysis of the Universo Profesional codebase (master branch, commits through c43a6cb).

