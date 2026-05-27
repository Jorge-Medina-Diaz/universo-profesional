# Universo Profesional — Graph-RAG arquitectura

Este documento captura la arquitectura del núcleo de hipergrafo personal +
ontología ESCO + retrieval híbrido que reemplaza el modelo plano de
entidades enumeradas. Sprints M → R del plan v2.

## Topología

```
                            ┌──────────────────────────────────────────┐
                            │            CHAT AGÉNTICO (28)            │
                            │  CopilotKit AG-UI · HITL proposal cards  │
                            └────────────────────┬─────────────────────┘
                                                 │
                               write contract: ADD / UPDATE / DELETE / NOOP
                                                 ▼
        ┌───────────────────────────────────────────────────────────────┐
        │              UNIVERSE GRAPH SERVICE (UGS)                     │
        │  • Coherence v2 (cross-type, ontology-anchored)               │
        │  • ESCO entity linker (NER → cand. → rerank → quarantine)     │
        │  • FeatureReranker (Jaro-Winkler + Jaccard + exact bonus)     │
        │  • Outlier detection (IsoForest + LOF on PCA-64)              │
        │  • Episode tracker (sesiones de chat = :Episode nodes)        │
        │  • Edge materialisation (derived_from_*, linked_*, …)         │
        └──────────────┬──────────────────────────────┬─────────────────┘
                       │                              │
                       ▼                              ▼
        ┌─────────────────────────────┐  ┌────────────────────────────┐
        │  PERSONAL GRAPH             │  │  ONTOLOGY BACKBONE          │
        │  Apache AGE                 │  │  Apache AGE                 │
        │  graph: universe_personal   │  │  graph: universe_ontology   │
        │  Vertex labels:             │  │  Nodes:                     │
        │   :Entity {kind: ...}       │  │   :Occupation (~3k)         │
        │   :Evidence                 │  │   :EscoSkill  (~14k)        │
        │   :Signal                   │  │   :ISCOGroup                │
        │   :Episode                  │  │  Edges:                     │
        │   :Community                │  │   :SKOS_BROADER             │
        │   :Goal                     │  │   :SKOS_NARROWER            │
        │  Edge types:                │  │   :ESSENTIAL_FOR            │
        │   :DEMONSTRATES             │  │   :OPTIONAL_FOR             │
        │   :PART_OF                  │  │   :ISCO_GROUP_OF            │
        │   :USES_TECH                │  │                             │
        │   :OCCURRED_IN              │  │  (read-only; refreshed por  │
        │   :PRODUCED                 │  │  release ESCO trimestral)   │
        │   :EVIDENCES_SIGNAL         │  │                             │
        │   :SUPERSEDES               │  │  Personal nodes link aquí   │
        │   :DERIVED_FROM             │  │  via graph_esco_links table │
        │   :TOUCHED_IN               │  │  (cross-graph edges no son  │
        │   :MEMBER_OF                │  │  posibles en AGE, así que   │
        │  Multi-tenant: property     │  │  usamos una tabla puente).  │
        │  `user_id` en cada vértice  │  │                             │
        │  + arista.                  │  │  Fallback: si ESCO devuelve │
        │                             │  │  ORPHAN, se consulta la     │
        │  Aristas temporales:        │  │  ontología custom de skills │
        │   {valid_from, valid_to}    │  │  (MCP, RAG, CrewAI, etc.)   │
        │  NULL valid_to = activa     │  └────────────────────────────┘
        └─────────────┬───────────────┘
                      │
                      ▼
        ┌───────────────────────────────────────────────────────────────┐
        │             HYBRID RETRIEVER (3 carriles + RRF k=60)          │
        │  ① BM25 (Postgres tsvector + GIN indexes)                     │
        │  ② Dense (pgvector HNSW, OpenAI text-embedding-3-small)       │
        │  ③ PPR    (igraph snapshot/usuario, semilla por dense top-3)  │
        │  fusión Reciprocal Rank Fusion (Cormack k=60)                 │
        │  Fase 2 (futura): + SPLADE + community summaries (Leiden)     │
        └───────────────────────────┬───────────────────────────────────┘
                                    │
                                    ▼
                          ┌─────────────────────────┐
                          │     AGENTS (28)         │
                          │  Tools nuevos:          │
                          │   • universe_retrieve   │
                          │   • get_graph_neighbors │
                          │   • explain_path        │
                          │   • coherence_upsert v2 │
                          │     (op_hint + session) │
                          │   • query_graph         │
                          │   • record_feedback     │
                          └────────────┬────────────┘
                                       │
                                       ▼
        ┌───────────────────────────────────────────────────────────────┐
        │                       FRONTEND                                │
        │   /universe — 3 lentes sobre el mismo grafo:                  │
        │     • Graph     — sigma.js + ForceAtlas2 (default)            │
        │     • Outline   — Tana-style (kinds agrupados)                │
        │     • Trajectory — timeline (Sprint R+ expande con Episodes)  │
        │   Chat sidebar — graph lens cuando el agente fija focus       │
        │   Discovery progress widget — score + coverage + SSE          │
        └───────────────────────────────────────────────────────────────┘
```

## Decisiones clave

| Pregunta | Elección | Motivo |
|---|---|---|
| Backend de grafo | **Apache AGE + pgvector** en una sola Postgres | Multi-tenant trivial por `user_id`; ACID con vectores y relacional; sin ops extra |
| Ontología externa | **ESCO** subset ES+EN | Oficial UE, multilingüe, gratuita, hierarchica (SKOS), ~17k conceptos |
| Retrieval híbrido | **3 carriles + RRF k=60** | Estándar de la literatura; SPLADE + community summaries en fase 2 |
| Hipergrafo | **Multigraph + nodos Evidence reificados** | Isomorfo a hyperedge, sin DB hypergraph dedicada |
| UI primaria | **Conversación + lente de grafo** | Móvil-first; el grafo es lente secundaria, no la UX primaria |
| Cross-encoder ESCO | **FeatureReranker local** (sin GPU) | Determinista, rápido, interpretable; reduce falsos positivos de términos polisémicos |

## Componentes (backend)

### `src/graph/`

- **`domain/schema.py`** — constantes de labels y edge types (NUEVO)
- **`domain/registry.py`** — `GRAPH_REGISTRY` único, reemplaza al flat
  `ENTITY_REGISTRY` de Sprint G. Cada entrada describe SQL table, name
  field, embedding text, `onto_link_kind`.
- **`domain/nodes.py`** — dataclasses para EntityNode, EvidenceNode,
  SignalNode, EpisodeNode, etc.
- **`domain/edges.py`** — `GraphEdge` con campos temporales.
- **`domain/esco_types.py`** — `EscoCandidate`, `EscoLinkResult`, `LinkState`.
- **`domain/custom_skills_ontology.py`** — ontología fallback para skills de IA
  no presentes en ESCO (MCP, RAG, CrewAI, etc.). Cargada en memoria (<100
  conceptos) e indexada en pgvector junto a ESCO.

- **`infrastructure/age_client.py`** — wrapper `cypher()` que serializa
  parámetros como JSON y los pasa con `CAST(:p AS agtype)` (porque AGE
  exige que el 3er arg de `cypher()` sea un Param node, no un literal).
- **`infrastructure/ontology_loader.py`** — ingesta CSV de ESCO →
  `universe_ontology` + tabla `ontology_embeddings`. Idempotente vía
  `graph_ingest_meta`.

- **`application/universe_graph.py`** — `UniverseGraphService` con
  `upsert_entity / soft_delete_entity / upsert_edge / expire_edge /
  get_entity / neighbors`. La clase usa `MERGE … SET COALESCE(...)` en
  lugar de `MERGE … ON CREATE SET` porque AGE 1.5 no soporta este último.
- **`application/esco_linker.py`** — `EscoEntityLinker` con normalize +
  candidate generation (pgvector) + `FeatureReranker` + threshold-based
  resolution. Devuelve `LINKED / SUGGESTED / ORPHAN / ERROR`.
  - Threshold auto-link: **0.86**
  - Threshold quarantine (HITL): **0.70**
  - Fallback ORPHAN → ontología custom (`custom_skills_ontology.py`).
- **`application/cross_encoder.py`** — `FeatureReranker` stateless.
  Re-scorea candidatos ESCO con señales locales:
  - Jaro-Winkler similarity (`jellyfish`) — 0.35
  - Token Jaccard overlap — 0.25
  - Exact prefix/suffix bonus — 0.20
  - Original rank decay — 0.20
  No requiere GPU ni dependencias pesadas.
- **`application/outlier_detection.py`** — IsoForest + LOF agreement
  sobre embeddings reducidos a 64-d con PCA. Flag se persiste en
  `entity_quarantine` con razón `outlier`.
- **`application/retrieval.py`** — `BM25Retriever`, `DenseRetriever`,
  `PPRRetriever`, `reciprocal_rank_fusion`, `hybrid_retrieve`.
  Snapshot igraph LRU (max 200 usuarios). Lanes corren secuencialmente
  por la restricción de asyncpg (1 op por conexión).
- **`application/episodes.py`** — `ensure_episode / record_touch /
  close_episode`. Episode id derivado vía SHA-256 del chat_session_id.

- **`interfaces/api/graph_router.py`** — endpoints
  `/api/v1/graph/{entity_id, retrieve, snapshot, neighbors, quarantine,
  edges}`.

### `src/coherence/application/coherence_v2.py`

Nuevo módulo que extiende el dual-write con:
- `post_upsert()` — ESCO linking + edge materialisation + snapshot
  invalidation. Best-effort: errores se loguean pero no propagan.
- `_attach_esco_edge()` — escribe `graph_esco_links` (tabla puente
  entre grafo personal y backbone ontológico).
- `_open_esco_quarantine()` — crea fila en `entity_quarantine` para
  HITL.
- `_materialise_edges()` — traduce `derived_from_*`, `linked_skill_ids`,
  `related_project_id`, `superseded_by` en aristas tipadas.
- `flag_outliers_for_user()` — usado por el curator.
- `resolve_quarantine()` — invocado por el endpoint REST cuando el
  usuario elige una opción ESCO desde el chat.
- `find_by_esco_uri()` — dedup cross-tipo: dos entidades que linkean
  al mismo ESCO URI son la misma "skill semántica".

### `src/agents/tools/`

- **`retrieval_tools.py`** — `universe_retrieve`, `get_graph_neighbors`,
  `explain_path`. Reemplazan en gran parte a `search_universe`,
  `find_existing`, `search_rubrics`.
- **`graph_query_tools.py`** — `query_graph`, `explain_graph_query`.
  Text2Cypher para consultas en lenguaje natural sobre AGE.
- **`learning_tools.py`** — `record_agent_feedback`. Alimenta el
  self-learning loop desde el flujo HITL.
- **`ui_widgets.py`** — añade `propose_esco_disambiguation`,
  `propose_edge_creation`, `propose_edge_deletion`, `propose_document_generation`.

## ESCO linking pipeline

```
Input text (e.g. "Docker")
    │
    ▼
Normalise (NFKC, lowercase, abbreviation expansion)
    │
    ▼
Embed → pgvector top-K cosine on ontology_embeddings
    │
    ▼
FeatureReranker re-scores candidates:
  • Jaro-Winkler(label, query)     × 0.35
  • Jaccard(tokens)                × 0.25
  • Exact substring bonus          × 0.20
  • Rank decay (1.0 → 0.85 …)      × 0.20
    │
    ▼
Threshold resolution:
  rerank_score ≥ 0.86  →  LINKED     (auto, esco_uri persisted)
  rerank_score ≥ 0.70  →  SUGGESTED  (quarantine, HITL card)
  else                 →  ORPHAN     (fallback to custom_skills_ontology)
```

El threshold 0.86 reduce falsos positivos de términos polisémicos
("Java" la isla vs. "Java" el lenguaje): aunque el embedding pueda estar
cerca, el Jaro-Winkler y el Jaccard penalizan el desajuste de etiquetas.

## Ontología custom fallback

Cuando ESCO devuelve `ORPHAN` (sin candidato por encima de 0.70), el linker
consulta `src/graph/domain/custom_skills_ontology.py`.  Es una ontología
curada en memoria (<100 conceptos) que cubre skills de IA/LLM no presentes
en ESCO:

- `up:ai/mcp` — Model Context Protocol
- `up:ai/rag-pipeline` — Retrieval-Augmented Generation
- `up:ai/crewai` — Framework multi-agente
- `up:ai/vector-databases` — pgvector, Pinecone, Weaviate
- …

Cada concepto lleva `uri`, `pref_label_es/en`, `description` y `related_uris`.
Se indexan en pgvector junto a ESCO para que la búsqueda densa los encuentre
también.  Se puede ampliar añadiendo entradas a `_CUSTOM_SKILLS`.

## Componentes (frontend)

- **`src/graph/api.ts`** — cliente HTTP para `/api/v1/graph/*`.
- **`src/graph/GraphView.tsx`** — sigma.js + graphology + ForceAtlas2.
  Colores por `kind`, tamaño por degree centrality.
- **`src/chat/cards/EscoDisambigCard.tsx`** — HITL para quarantine ESCO.
- **`src/pages/UniversePage.tsx`** — reescrita. 3 lentes (Graph,
  Outline, Trajectory), filtros por kind, sidebar con
  ProfileCompleteness + SuggestionBar.
- **`src/chat/actions.tsx`** — registra los handlers
  `propose_esco_disambiguation`, `propose_edge_creation`,
  `propose_edge_deletion`, `propose_document_generation`, `propose_cover_letter`.
- **`src/widgets/DiscoveryProgress.tsx`** — widget de score 0-100 con SSE
  en tiempo real.

## Migraciones

- **0014** — `CREATE EXTENSION age`, dos graphs (`universe_personal`,
  `universe_ontology`), tablas sidecar:
  - `graph_ingest_meta` — versión ESCO importada.
  - `entity_quarantine` — RLS por usuario, ESCO low-confidence y outliers.
  - `ontology_embeddings` — pgvector HNSW.
  - `graph_entity_embeddings` — sidecar de embeddings personales.
  - `graph_edge_audit` — log temporal de aristas.
- **0015** — `tsv tsvector` GENERATED ALWAYS sobre 11 tablas de entidades
  + `ontology_search` (tabla puente con tsv vía trigger por el
  `IMMUTABLE` que generated requiere).

## Operaciones

### Ingestar ESCO

El seeding es automático al levantar Docker Compose (`cvs-esco-seed`).
Para forzar una re-ingesta manual:

```bash
./scripts/seed-esco.sh --force
# o desde el container:
docker compose exec backend python -m scripts.seed_esco --force
```

Para verificar:

```bash
docker compose exec backend python -m scripts.ingest_esco --verify
```

### Reconstruir AGE desde cero

```bash
docker compose stop postgres backend worker
docker volume rm cvs-saas_postgres_data
docker compose up -d postgres
docker exec cvs-backend alembic upgrade head
```

### Performance esperada

| Operación | p50 | p95 |
|---|---|---|
| `coherence_upsert` (skill) | 80 ms | 200 ms |
| `hybrid_retrieve` (warm cache) | 10 ms | 50 ms |
| `hybrid_retrieve` (cold cache) | 800 ms | 1500 ms |
| `GET /api/v1/graph/snapshot` (500 nodos) | 250 ms | 600 ms |
| `esco_linker` (1 skill, cold) | 30 ms | 80 ms |

Cold snapshot loading domina el cold-start. La invalidación se
dispara desde `coherence_v2.post_upsert()` después de cada escritura,
así que el grafo siempre se reconstruye al cabo de un par de minutos
de inactividad. Para usuarios muy grandes (>10k nodos), Sprint R+
debería persistir snapshots por usuario en pickle dentro de Redis.

## Convenciones de Cypher en AGE 1.5

Estas tres "navajas" descubiertas durante Sprint M-O son críticas
para no perder tiempo el próximo cambio:

1. **`MERGE … ON CREATE SET / ON MATCH SET` no funciona**. Usar
   `MERGE … SET valid_from = COALESCE(e.valid_from, $now)`.
2. **`cypher('graph', $$ ... $$, $arg)` exige que `$arg` sea un Param
   node** del planner. `'literal'::agtype` da
   `InvalidParameterValueError: third argument of cypher function must
   be a parameter`. Solución: `CAST(:cypher_params AS agtype)` con bind
   real desde SQLAlchemy.
3. **`create_graph()` lanza `InvalidSchemaName` (3F000) si el grafo
   existe, no `XX000`**. Pre-checkear con `SELECT 1 FROM
   ag_catalog.ag_graph WHERE name = ...`.
4. **`search_path` `ag_catalog,public`** hace que `CREATE TABLE …`
   aterrice en `ag_catalog`. Mantener `public` primero.

## Cutover de legacy (Sprint R)

El módulo de Sprint R contiene el script `backend/scripts/migrate_legacy_to_graph.py`
que materialisa las relaciones implícitas (tabla `evidences`,
`linked_skill_ids`, `evidence_refs`, FKs sueltas) como aristas
tipadas en `universe_personal`. Se ejecuta con `--dry-run` por defecto;
añadir `--apply` para escribir.

Después de la migración exitosa, la **migración 0017** dropea:

- Tabla `evidences`
- Tabla `user_rubric_signals` (reemplazada por nodos `:Signal`)
- Columnas `artifacts.linked_skill_ids`, `artifacts.linked_project_id`
- Columnas `skills.evidence_refs`
- Columnas `architecture_decisions.related_project_id`,
  `architecture_decisions.superseded_by`

> ⚠ **Esta migración es destructiva**. Hacer dump pre-aplicación.
> El plan asume que el ETL de cutover ha verificado que el grafo
> contiene las mismas aristas que las columnas legacy antes del drop.
