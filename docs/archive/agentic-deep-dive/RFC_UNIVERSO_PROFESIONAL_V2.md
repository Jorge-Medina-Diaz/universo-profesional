# RFC: Bases Definitivas del Sistema de Conocimiento y Agentes — Universo Profesional v2

> **Estado:** Draft para revisión arquitectónica  
> **Fecha:** 2026-05-26  
> **Autor:** Investigación Agente AI  
> **Alcance:** Re-definición completa del subsistema de conocimiento (`knowledge/`, `graph/`, `coherence/`, `agents/`) sin restricciones de legacy.  

---

## Tabla de Contenidos

1. [Diagnóstico: Por qué el modelo actual alcanza su techo](#1-diagnóstico-por-qué-el-modelo-actual-alcanza-su-techo)
2. [Principios Rectores](#2-principios-rectores)
3. [El Universo como Property Graph Temporal](#3-el-universo-como-property-graph-temporal)
4. [Ontología ESCO: Grafo de Referencia Enlazado](#4-ontología-esco-grafo-de-referencia-enlazado)
5. [Arquitectura de RAG Híbrido: Vector + Graph + Temporal](#5-arquitectura-de-rag-híbrido-vector--graph--temporal)
6. [Motor de Coherencia v2: Entity Resolution Semántico](#6-motor-de-coherencia-v2-entity-resolution-semántico)
7. [Arquitectura de Agentes Especializados](#7-arquitectura-de-agentes-especializados)
8. [Memoria Estructurada del Universo](#8-memoria-estructurada-del-universo)
9. [Versionado como Lineage Temporal](#9-versionado-como-lineage-temporal)
10. [Roadmap de Implementación](#10-roadmap-de-implementación)
11. [Anexo: Esquema de Graph completo](#11-anexo-esquema-de-graph-completo)

---

## 1. Diagnóstico: Por qué el modelo actual alcanza su techo

### 1.1 Limitaciones del modelo relacional puro

Nuestro MVP usa PostgreSQL relacional + pgvector para chunks + Apache AGE "planificado". Esta arquitectura presenta grietas fundamentales para nuestro caso de uso:

| Problema | Consecuencia en el MVP | Ejemplo concreto |
|----------|----------------------|------------------|
| **Relaciones implícitas** | Las FK no expresan semántica de relación | `experience_id → project_id` no dice si el proyecto fue *interno*, *cliente* o *open-source* |
| **Temporalidad ausente** | No hay modelado nativo de "vigencia" | Una skill adquirida en 2018 y otra en 2025 son filas iguales |
| **Sin inferencia de trayectoria** | No podemos razonar sobre progresión de carrera | "¿Este candidato ha escalado de junior a senior en < 3 años?" requiere N joins complejos |
| **Chunks descontextualizados** | RAG por chunks pierde estructura | Un chunk sobre "Python" no sabe si es skill, proyecto, o título de job |
| **Merge ciego** | El motor de coherencia opera por similitud textual | "Data Engineer" y "Ingeniero de Datos" son tratados como entidades distintas sin ontología |

### 1.2 Qué necesitamos en su lugar

Un sistema donde:
- **Las entidades profesionales son nodos** (personas, skills, jobs, empresas, proyectos, certificaciones, títulos)
- **Las relaciones son edges tipados y propiedades** (`HAS_SKILL` con `level`, `acquired_at`, `source`; `WORKED_AT` con `role`, `from`, `to`, `team_size`)
- **El tiempo es una dimensión de primera clase** — no un campo más, sino parte del modelo de query
- **ESCO es un grafo de referencia enlazado** — nuestro grafo de usuario se ancla a conceptos normalizados
- **La recuperación es híbrida**: vector para similitud semántica, graph para relaciones y trayectorias, temporal para vigencia

---

## 2. Principios Rectores

1. **Graph-native, no graph-adjacent.** El grafo no es una capa de lectura sobre SQL; es el modelo de datos canónico. PostgreSQL relacional sirve como storage engine, AGE como graph engine, pgvector como vector engine — todo en una misma base de datos.

2. **Tiempo como eje primario.** Toda entidad y relación tiene validez temporal. El "Universo Profesional" es una película, no una foto fija.

3. **Ontología anclada.** Todo concepto profesional (skill, job title, industry) se enlaza al grafo ESCO. Esto habilita: matching multilingüe, inferencia de skills relacionadas, y estandarización de nomenclatura.

4. **Coherencia por entity resolution, no por heurística.** El merge de entidades duplicadas se resuelve mediante blocking semántico + embedding similarity + reglas declarativas, no por string matching.

5. **Agentes especializados, no generalistas.** Un monolito que "hace todo con el CV" no escala. Queremos un equipo de agentes estrechos con roles definidos y fronteras de seguridad explícitas.

6. **Versionado = lineage.** Cada mutación del universo deja un rastro de grafo. El versionado no es una tabla de snapshots; es un grafo temporal donde `[:REPLACED_BY]` y `[:SUPERSEDED]` son relaciones de primera clase.

---

## 3. El Universo como Property Graph Temporal

### 3.1 Modelo de datos: Property Graph sobre Apache AGE

Apache AGE soporta el modelo **Labeled Property Graph (LPG)** via openCypher. Este es nuestro modelo canónico.

#### Nodos principales

| Label | Propiedades clave | Descripción |
|-------|-------------------|-------------|
| `Person` | `uuid`, `name`, `email`, `created_at` | Entidad persona (el usuario) |
| `Experience` | `uuid`, `title`, `company_name`, `from_date`, `to_date`, `description`, `employment_type` | Puesto de trabajo o rol |
| `Education` | `uuid`, `institution`, `degree`, `field`, `from_date`, `to_date` | Formación académica |
| `Skill` | `uuid`, `name`, `esco_code`, `category` | Habilidad (anclada a ESCO cuando sea posible) |
| `Project` | `uuid`, `name`, `description`, `url` | Proyecto realizado |
| `Certification` | `uuid`, `name`, `issuer`, `issued_at`, `expires_at` | Certificación profesional |
| `Publication` | `uuid`, `title`, `venue`, `published_at` | Publicación académica o técnica |
| `Language` | `code`, `name` | Idioma |

#### Relaciones principales

| Tipo | Origen → Destino | Propiedades |
|------|-------------------|-------------|
| `HAS_EXPERIENCE` | Person → Experience | `confidence: float`, `verified: bool` |
| `HAS_EDUCATION` | Person → Education | `confidence: float` |
| `HAS_SKILL` | Person → Skill | `level: enum`, `acquired_at: date`, `source: text`, `confidence: float` |
| `REQUIRED_SKILL` | Experience → Skill | `level: enum`, `is_primary: bool` |
| `WORKED_ON` | Experience → Project | `role_in_project: text` |
| `HAS_CERTIFICATION` | Person → Certification | `status: enum` |
| `SPEAKS` | Person → Language | `proficiency: enum` |
| `PRECEDED_BY` | Experience → Experience | `transition_type: enum` | ← **clave para trayectoria** |
| `ESCO_MATCH` | Skill → EscoSkill | `match_score: float`, `match_type: enum` | ← **anclaje ontológico** |

### 3.2 Consultas de ejemplo que el modelo relacional no puede hacer eficientemente

```cypher
// Trayectoria completa de una persona (ordenada cronológicamente)
MATCH path = (p:Person {uuid: $user_id})-[:HAS_EXPERIENCE]->(e:Experience)
WITH e ORDER BY e.from_date
RETURN [node in nodes(path) | node.title] AS career_path

// Skills implícitas por transitividad (si tiene "Neural Networks", probablemente tiene "Python")
MATCH (p:Person)-[:HAS_SKILL]->(s:Skill)-[:ESCO_PREREQUISITE*1..3]->(implied:Skill)
WHERE NOT (p)-[:HAS_SKILL]->(implied)
RETURN implied.name AS suggested_skill

// "Quién ha seguido una trayectoria similar"
MATCH (me:Person {uuid: $my_id})-[:HAS_EXPERIENCE]->(my_exp:Experience)
MATCH (other:Person)-[:HAS_EXPERIENCE]->(their_exp:Experience)
WHERE other <> me AND my_exp.title =~ their_exp.title
  AND abs(duration(my_exp.from_date, my_exp.to_date) - 
           duration(their_exp.from_date, their_exp.to_date)) < duration('P6M')
RETURN other.name, count(*) AS similarity_score
ORDER BY similarity_score DESC

// Evolución temporal de skills
MATCH (p:Person {uuid: $user_id})-[hs:HAS_SKILL]->(s:Skill)
RETURN s.name, hs.acquired_at, hs.level
ORDER BY hs.acquired_at
```

### 3.3 Sync relacional → graph

El modelo relacional (tablas `experiences`, `educations`, etc.) sigue siendo la **fuente de verdad transaccional**. Pero cada escritura válida dispara un evento que materializa/mutate el nodo/edge correspondiente en AGE.

```python
# Patrón: Unit of Work transaccional + materialización async
async with with_user_session(user_id) as session:
    # 1. Escritura relacional (fuente de verdad)
    session.add(new_experience)
    await session.commit()
    
    # 2. Evento de dominio publicado
    await event_bus.publish(ExperienceCreated(experience_id=exp.id))

# 3. Materializador async (worker arq) escucha el evento
@worker.task
async def materialize_experience_to_graph(event: ExperienceCreated):
    async with age_graph_session() as g:
        await g.run("""
            MATCH (p:Person {uuid: $user_id})
            CREATE (e:Experience {uuid: $exp_id, title: $title, ...})
            CREATE (p)-[:HAS_EXPERIENCE {confidence: 1.0}]->(e)
        """, user_id=..., exp_id=...)
```

---

## 4. Ontología ESCO: Grafo de Referencia Enlazado

### 4.1 Por qué ESCO

ESCO (European Skills, Competences, Qualifications and Occupations) es la taxonomía oficial de la Comisión Europea con:
- ~3,000 occupations
- ~13,000 skills/competences
- ~5,500 qualifications
- Relaciones jerárquicas, de equivalencia, y occupation-skill associations (`isEssentialFor`, `isOptionalFor`)
- Disponible en 28 idiomas

Para nuestro caso de uso español/B2C europeo, ESCO es el anclaje ontológico perfecto.

### 4.2 Carga de ESCO como subgrafo de referencia

En el mismo grafo AGE (namespace separado `esco_graph`), cargamos ESCO completo:

```cypher
// Crear nodo ESCO skill
CREATE (s:EscoSkill {
    code: "S6361",
    preferredLabel: "develop software prototypes",
    altLabels: ["prototype development", "software prototyping"],
    description: "...",
    hierarchy: ["T1", "T2", "T3"]  // broad → narrow
})

// Crear relación jerárquica
MATCH (parent:EscoSkill {code: "S6360"}), (child:EscoSkill {code: "S6361"})
CREATE (child)-[:ESCO_BROADER_THAN]->(parent)

// Crear relación occupation-skill
MATCH (occ:EscoOccupation {code: "O1234"}), (skill:EscoSkill {code: "S6361"})
CREATE (skill)-[:IS_ESSENTIAL_FOR {weight: 1.0}]->(occ)
```

### 4.3 Entity Linking: Conectar nuestro grafo a ESCO

Cada `Skill` o `Experience` del usuario debe enlazarse al grafo ESCO. Esto no es un simple string match; requiere un pipeline de **entity linking**:

```
Input: Skill.name = "Desarrollo de prototipos de software"
  │
  ├──▶ Blocking: Candidatos ESCO con overlap de tokens o similaridad embedding
  │       └── Top-5: S6361, S6362, S6363, S6364, S6365
  │
  ├──▶ Reranking: LLM-as-judge con prompt de "exact synonym"
  │       └── Winner: S6361 (score: 0.94)
  │
  └──▶ Crear edge: (Skill)-[:ESCO_MATCH {score: 0.94, type: "exact"}]->(EscoSkill)
```

**Implementación:**
- Embedding de todos los `preferredLabel` + `altLabels` ESCO en pgvector
- Blocking por similaridad coseno + fuzzy string match
- Reranking con LLM (Claude/GPT) para decisión final
- Cache de enlaces ya resueltos para evitar re-computo

### 4.4 Beneficios del anclaje ESCO

1. **Normalización multilingüe**: "Data Engineer" (EN), "Ingeniero de Datos" (ES), "Ingénieur de données" (FR) → mismo nodo ESCO
2. **Inferencia de skills**: Si el usuario tiene skill A y ESCO dice A `[:REQUIRES]` B, sugerimos B
3. **Matching semántico**: Matching CV-JD no es keyword search; es navegación por grafo ESCO
4. **Career guidance**: Las transiciones occupation→occupation en ESCO guían recomendaciones de carrera

---

## 5. Arquitectura de RAG Híbrido: Vector + Graph + Temporal

### 5.1 Tres motores de retrieval en uno

Nuestro RAG no es "recuperar chunks y generar". Es un sistema de **evidencia híbrida**:

| Motor | Responsabilidad | Tecnología |
|-------|----------------|------------|
| **Vector** | Similitud semántica sobre descripciones, chunks, narrativas | pgvector (HNSW) + embeddings locales/multilingües |
| **Graph** | Relaciones, trayectorias, multi-hop reasoning, skills implícitas | Apache AGE (openCypher) |
| **Temporal** | Vigencia, secuencia, predicción de trayectoria | Filtros de fecha en queries + TKG snapshots |

### 5.2 Estrategias de retrieval según tipo de query

| Tipo de pregunta | Estrategia predominante | Ejemplo |
|------------------|------------------------|---------|
| "¿Cuál es mi experiencia en Python?" | Vector + Graph | Vector busca "Python", graph expande a proyectos y roles |
| "¿He trabajado en liderazgo técnico?" | Graph | Traversal de `Experience→Project→Skill` con `level = "lead"` |
| "¿Qué skill debería aprender next?" | Graph + Temporal | CareerPathKG: mi posición actual → transiciones comunes → skills gap |
| "Resume mi trayectoria en 2023" | Temporal | Filtro de fecha + agregación de subgraph |
| "¿Soy candidato para X rol?" | Graph + ESCO | Mi skill graph vs requirements graph del rol (vía ESCO) |

### 5.3 Hybrid Search con RRF en PostgreSQL

Combinamos BM25 (full-text PostgreSQL) + Vector (pgvector) + Graph (AGE) mediante **Reciprocal Rank Fusion**:

```sql
-- Función RRF en PostgreSQL
CREATE OR REPLACE FUNCTION rrf_score(rank INT, k INT DEFAULT 60)
RETURNS NUMERIC AS $$
BEGIN
    RETURN 1.0 / (k + rank);
END;
$$ LANGUAGE plpgsql IMMUTABLE;

-- Query híbrida: vector + full-text + graph boost
WITH vector_results AS (
    SELECT id, embedding <=> query_embedding AS distance,
           row_number() OVER (ORDER BY embedding <=> query_embedding) AS rank
    FROM knowledge_chunks
    ORDER BY distance LIMIT 40
),
text_results AS (
    SELECT id, ts_rank_cd(content_tsv, query) AS score,
           row_number() OVER (ORDER BY ts_rank_cd DESC) AS rank
    FROM knowledge_chunks
    WHERE content_tsv @@ plainto_tsquery('spanish', $1)
    LIMIT 40
),
graph_results AS (
    -- IDs de chunks relacionados a entidades del grafo que matchean
    SELECT chunk_id AS id, 1.0 AS graph_boost,
           row_number() OVER (ORDER BY graph_relevance DESC) AS rank
    FROM graph_chunk_links
    WHERE entity_id IN (SELECT id FROM graph_matches WHERE ...)
    LIMIT 40
)
SELECT 
    COALESCE(v.id, t.id, g.id) AS id,
    COALESCE(rrf_score(v.rank), 0) * 0.5 +
    COALESCE(rrf_score(t.rank), 0) * 0.3 +
    COALESCE(rrf_score(g.rank), 0) * 0.2 AS final_score
FROM vector_results v
FULL OUTER JOIN text_results t ON v.id = t.id
FULL OUTER JOIN graph_results g ON COALESCE(v.id, t.id) = g.id
ORDER BY final_score DESC
LIMIT 10;
```

### 5.4 Graph RAG: De query a openCypher

Para queries estructuradas, el agente genera openCypher en lugar de confiar en embeddings:

```python
# Agno Agent con Knowledge Graph
from agno.agent import Agent
from agno.knowledge.age import AgeKnowledgeBase

kg_agent = Agent(
    model=OpenAIChat(id="gpt-5.4"),
    knowledge=AgeKnowledgeBase(
        graph_name="universe_graph",
        schema=UNIVERSE_SCHEMA,  # metadatos del grafo para el LLM
    ),
    search_knowledge=True,  # Agno decidirá cuándo usar KG
    instructions=[
        "Para preguntas sobre trayectoria, relaciones o skills, genera openCypher.",
        "Para preguntas narrativas, usa hybrid search sobre chunks.",
        "Siempre valida que las queries openCypher usen labels y relaciones existentes.",
    ],
)
```

**Text2Cypher accuracy:** Según Gupta & Tadayon (2026), text-to-Cypher bien schematizado alcanza >90% accuracy para queries de complejidad media.

---

## 6. Motor de Coherencia v2: Entity Resolution Semántico

### 6.1 El problema del MVP

El motor de coherencia actual hace upsert con reglas de merge declarativas, pero:
- No resuelve entidades duplicadas semánticamente ("Google" vs "Google Inc." vs "Google LLC")
- No detecta skills equivalentes en diferentes idiomas
- No maneja la evolución temporal de una misma entidad ("Junior Dev" → "Senior Dev" son el mismo "yo" en diferentes tiempos)

### 6.2 Pipeline de Entity Resolution (ER)

```
Input: Nueva entidad (Experience/Skill/Education)
  │
  ├──▶ 1. BLOCKING
  │       └── Agrupar candidatos por: embeddings, phonetic keys, tokens compartidos
  │
  ├──▶ 2. PAIRWISE MATCHING
  │       └── Para cada candidato, calcular:
  │           - Embedding similarity (label + description)
  │           - String similarity (Jaro-Winkler para nombres cortos)
  │           - Graph similarity (vecindario en el grafo)
  │           - Temporal overlap (¿coexistieron en el tiempo?)
  │
  ├──▶ 3. CLUSTERING
  │       └── Connected components: si A≈B y B≈C, A y C van al mismo cluster
  │
  ├──▶ 4. MERGE DECLARATIVO
  │       └── Para cada campo del cluster, regla de resolución:
  │           - name: longest non-null string
  │           - dates: earliest from, latest to
  │           - description: concatenate con separador
  │           - esco_match: el de mayor confidence
  │
  └──▶ 5. PROVENANCE
          └── Crear nodo `MergeEvent` con edges `[:MERGED_INTO]` a entidades originales
```

### 6.3 Reglas de merge por tipo de entidad

```yaml
# coherence_rules.yaml
Experience:
  blocking_keys:
    - phonetic(company_name)
    - date_range_overlap(from_date, to_date, tolerance: 90d)
  matching_threshold: 0.82
  field_resolution:
    title: "longest_non_null"
    company_name: "esco_linked_or_longest"
    description: "concatenate_unique"
    from_date: "earliest"
    to_date: "latest"
    skills: "union"

Skill:
  blocking_keys:
    - embedding_nearest( top_k: 10 )
    - esco_code
  matching_threshold: 0.88
  field_resolution:
    name: "esco_preferred_label"
    level: "max"
    acquired_at: "earliest"
    esco_code: "most_confident"
```

### 6.4 Integración con el grafo

El merge no modifica entidades "in-place". En el grafo temporal:

```cypher
// Entidades originales marcadas como merged
MATCH (e1:Experience {uuid: "exp-123"}), (e2:Experience {uuid: "exp-456"})
CREATE (merged:Experience {uuid: "exp-merged-789", ...campos resueltos...})
CREATE (e1)-[:MERGED_INTO {at: datetime(), reason: "entity_resolution"}]->(merged)
CREATE (e2)-[:MERGED_INTO {at: datetime(), reason: "entity_resolution"}]->(merged)

// El nuevo nodo hereda todas las relaciones
MATCH (e1)-[r]->(target)
CREATE (merged)-[r2:REL_TYPE(r)]->(target)
```

Esto preserva **provenance** completo y permite "deshacer" merges si el usuario corrige.

---

## 7. Arquitectura de Agentes Especializados

### 7.1 Equipo de 4 agentes

Inspirado en Dash v2 y en la taxonomía de Context Providers, definimos un equipo de agentes con fronteras de seguridad reales (no solo prompts):

| Agente | Rol | Herramientas | Frontera de seguridad |
|--------|-----|--------------|----------------------|
| **Universe Navigator** (Líder) | Entender intención, ruteo, síntesis narrativa | `query_universe`, `query_esco`, `generate_summary` | Sin acceso directo a DB. Solo orquesta. |
| **Graph Analyst** | Consultas estructuradas, traversal, análisis de trayectoria | `run_cypher`, `get_skill_graph`, `find_career_paths` | Read-only sobre AGE + pgvector. No muta. |
| **Document Engineer** | Generar/modificar CVs, cover letters, exportar PDF/DOCX | `render_template`, `compile_document`, `preview_layout` | Solo acceso a `templates/` y `documents/` storage. |
| **Coherence Guardian** | Validar merges, detectar conflictos, resolver duplicados | `suggest_merge`, `validate_consistency`, `resolve_entity` | Solo invocable por el system, no por usuario directo. |

### 7.2 Patrón Context Provider aplicado

Cada fuente de datos expone exactamente 2 herramientas al agente principal:

```python
# Context Provider: Universe Data
universe_provider = UniverseContextProvider(
    id="universe",
    model=OpenAIChat(id="gpt-5.4-mini"),  # Modelo más barato para sub-agente
    read_only=True,
)

# Context Provider: ESCO Ontology
esco_provider = EscoContextProvider(
    id="esco",
    model=OpenAIChat(id="gpt-5.4-mini"),
    read_only=True,
)

# Agente principal ve solo 4 herramientas
agent = Agent(
    model=OpenAIChat(id="gpt-5.4"),
    tools=[
        *universe_provider.get_tools(),      # query_universe, update_universe
        *esco_provider.get_tools(),           # query_esco
        *document_provider.get_tools(),       # generate_document
    ],
    instructions=[
        "Usa query_universe para consultar datos del usuario.",
        "Usa query_esco para normalizar conceptos profesionales.",
        "NUNCA generes Cypher directamente; delega a query_universe.",
    ],
)
```

### 7.3 HITL (Human-in-the-Loop) estructurado

Cuando el agente necesita una acción destructiva (merge, delete, generar CV final), el workflow pausa:

```python
from agno.tools import tool

@tool(requires_confirmation=True)
def update_universe(instruction: str) -> str:
    """Modifica el universo profesional del usuario. Requiere aprobación."""
    ...
```

El frontend recibe una `PauseEvent` con:
- Tipo de acción propuesta
- Diff visual (antes/después)
- Nivel de confianza del agente
- Botones: Aprobar / Modificar / Rechazar

---

## 8. Memoria Estructurada del Universo

### 8.1 Cuatro tiers adaptados al dominio profesional

| Tier | Nombre en nuestro dominio | Qué almacena | Implementación |
|------|--------------------------|--------------|----------------|
| **Working** | Contexto de sesión | Turnos de chat, tool calls, razonamiento intermedio | Memoria en-contexto del LLM + `session_state` |
| **Episodic** | Historial de interacciones | Resúmenes de sesiones, correcciones del usuario, preferencias de formato | PostgreSQL (`chat_sessions`) + Agno Storage |
| **Semantic** | Conocimiento del usuario | Hechos extraídos del universo: skills, preferencias de rol, estilo de CV, industria objetivo | Knowledge graph en AGE + memoria Agno (`update_memory_on_run=True`) |
| **Procedural** | Playbooks de generación | Plantillas preferidas, estructuras de CV que funcionaron, tono de comunicación | Reglas declarativas en `document_rules/` + procedural memory Agno |

### 8.2 Memoria episódica: qué funciona en nuestro caso de uso

Cada sesión de chat con el usuario genera un resumen estructurado:

```json
{
  "session_id": "sess-abc-123",
  "user_id": "user-xyz",
  "timestamp": "2026-05-26T10:00:00Z",
  "summary": "Usuario añadió experiencia en 'Data Engineer at Meta'. Solicitó CV en formato funcional. Prefiere no incluir fecha de nacimiento.",
  "facts_extracted": [
    {"type": "skill_added", "value": "Data Engineer", "entity_id": "exp-789"},
    {"type": "preference", "key": "cv_format", "value": "functional"},
    {"type": "preference", "key": "exclude_field", "value": "birth_date"}
  ],
  "corrections": [
    {"original": "Meta", "corrected": "Meta Platforms, Inc.", "field": "company_name"}
  ]
}
```

Estos resúmenes se indexan en pgvector y se inyectan en el contexto de nuevas sesiones vía `search_knowledge`.

### 8.3 Memoria procedural: aprender del feedback de CVs

Cuando un usuario edita un CV generado por el agente, la diferencia (diff) se almacena como **procedural memory**:

```json
{
  "rule_type": "template_preference",
  "trigger": "cv_generation",
  "pattern": "usuario eliminó la sección 'Intereses' en los últimos 3 CVs",
  "action": "omitir sección 'Intereses' por defecto; preguntar explícitamente si quiere incluirla"
}
```

---

## 9. Versionado como Lineage Temporal

### 9.1 El problema de "versionar un universo"

Nuestro MVP tiene `universe_change_log` (tabla relacional de auditoría). Pero un CV generado en enero refleja el universo *de enero*, no el actual. Necesitamos poder:
- Reconstruir el universo en cualquier punto del tiempo ("cómo era mi CV en marzo?")
- Generar un CV con el universo de hace 6 meses
- Comparar evolución entre dos fechas

### 9.2 Modelo temporal en el grafo

Cada nodo y edge tiene `valid_from` y `valid_to`:

```cypher
// Crear experiencia con validez temporal
CREATE (e:Experience {
    uuid: "exp-001",
    title: "Software Engineer",
    valid_from: datetime("2022-01-01"),
    valid_to: datetime("9999-12-31")  // vigente
})

// Cuando se actualiza, se crea un nuevo nodo temporal
MATCH (e:Experience {uuid: "exp-001"})
SET e.valid_to = datetime("2023-06-01")
CREATE (e2:Experience {
    uuid: "exp-001-v2",
    title: "Senior Software Engineer",
    valid_from: datetime("2023-06-01"),
    valid_to: datetime("9999-12-31")
})
CREATE (e)-[:SUPERSEDED_BY]->(e2)
```

### 9.3 Query temporal: "mi universo el 15 de marzo"

```cypher
MATCH (p:Person {uuid: $user_id})-[:HAS_EXPERIENCE]->(e:Experience)
WHERE e.valid_from <= datetime("2026-03-15") AND e.valid_to > datetime("2026-03-15")
RETURN e
```

### 9.4 Snapshots eficientes

En lugar de duplicar todo el grafo, usamos **deltas materializados**:
- Cada "versión" es un nodo `Snapshot` con timestamp
- Solo almacenamos `[:CHANGED_IN]` edges a entidades modificadas
- Reconstrucción: estado base + aplicar deltas hasta el snapshot deseado

```cypher
CREATE (snap:Snapshot {id: "snap-2026-Q1", created_at: datetime()})
WITH snap
MATCH (e:Experience)-[:MODIFIED_AT {timestamp: $snap_time}]->(change)
CREATE (snap)-[:INCLUDES {change_type: change.type}]->(e)
```

---

## 10. Roadmap de Implementación

### Fase 0: Infraestructura Graph (2 semanas)
- [ ] Confirmar Apache AGE 1.5+ compatible con PostgreSQL 16 + pgvector 0.8
- [ ] Definir schema de grafo completo (nodos, edges, propiedades, índices)
- [ ] Implementar materializador async (evento relacional → mutación en grafo)
- [ ] Migrador de datos existentes: tablas relacional → nodos/edges iniciales

### Fase 1: ESCO Integration (2 semanas)
- [ ] Pipeline de ingestión ESCO v1.2 (JSON-LD → openCypher)
- [ ] Entity linking pipeline: blocking + embedding + LLM reranking
- [ ] Vinculación automática de skills existentes del usuario a ESCO
- [ ] API de resolución de conceptos: `GET /esco/resolve?q="ing de datos"`

### Fase 2: Hybrid RAG (3 semanas)
- [ ] Configurar pgvector con HNSW para chunks + descripciones
- [ ] Implementar full-text search (GIN indexes) en PostgreSQL
- [ ] Construir RRF query uniendo vector + text + graph boost
- [ ] Text2Cypher scaffold: LLM + schema injection + validación sintáctica
- [ ] Evaluación: 100 queries representativos, medir precision@10 vs baseline

### Fase 3: Coherencia v2 (2 semanas)
- [ ] Implementar blocking semántico (embeddings + phonetic)
- [ ] Implementar pairwise matching con reglas configurables
- [ ] Implementar clustering (connected components)
- [ ] Implementar merge declarativo con provenance graph
- [ ] Reemplazar motor de coherencia actual por pipeline ER

### Fase 4: Agent Team (3 semanas)
- [ ] Refactorizar agente monolítico a 4 agentes especializados
- [ ] Implementar Context Providers (Universe, ESCO, Document)
- [ ] Implementar HITL con pausas estructuradas en frontend
- [ ] Integrar evals nativas de Agno (accuracy, reliability)

### Fase 5: Memoria y Versionado (2 semanas)
- [ ] Implementar 4-tier memory con Agno `update_memory_on_run`
- [ ] Implementar episodic memory con extracción estructurada
- [ ] Implementar versionado temporal en grafo (valid_from/valid_to)
- [ ] API de snapshot: `GET /universe/at/2026-03-15`

### Fase 6: Optimización y Evaluación (continuo)
- [ ] Benchmark de retrieval: precision, recall, latency
- [ ] Benchmark de entity resolution: F1 en merges reales
- [ ] User study: calidad de CVs generados vs MVP
- [ ] Hill-climb loop: eval suite → diagnóstico → mejora de prompts

---

## 11. Anexo: Esquema de Graph completo

### 11.1 Nodos

```cypher
// Person (el usuario)
(:Person {
    uuid: UUID,
    name: STRING,
    email: STRING,
    headline: STRING,
    summary: STRING,
    location: STRING,
    created_at: DATETIME,
    updated_at: DATETIME
})

// Experience (trabajo)
(:Experience {
    uuid: UUID,
    title: STRING,
    company_name: STRING,
    company_esco_code: STRING,      // anclaje a ESCO occupation
    from_date: DATE,
    to_date: DATE,                  // null si vigente
    description: STRING,
    employment_type: ENUM,          // full_time, part_time, freelance, internship
    location: STRING,
    valid_from: DATETIME,           // para versionado temporal
    valid_to: DATETIME
})

// Education
(:Education {
    uuid: UUID,
    institution: STRING,
    degree: STRING,
    field_of_study: STRING,
    from_date: DATE,
    to_date: DATE,
    grade: STRING,
    valid_from: DATETIME,
    valid_to: DATETIME
})

// Skill
(:Skill {
    uuid: UUID,
    name: STRING,
    category: STRING,               // technical, soft, language, tool
    esco_code: STRING,              // anclaje a ESCO
    esco_preferred_label: STRING,
    valid_from: DATETIME,
    valid_to: DATETIME
})

// ESCO reference nodes (subgrafo de referencia)
(:EscoSkill {
    code: STRING,
    preferredLabel: STRING,
    altLabels: LIST<STRING>,
    description: STRING,
    hierarchy: LIST<STRING>         // [broad, intermediate, narrow]
})

(:EscoOccupation {
    code: STRING,
    preferredLabel: STRING,
    altLabels: LIST<STRING>,
    description: STRING,
    isco_group: STRING
})

// Project
(:Project {
    uuid: UUID,
    name: STRING,
    description: STRING,
    url: STRING,
    from_date: DATE,
    to_date: DATE
})

// Certification
(:Certification {
    uuid: UUID,
    name: STRING,
    issuer: STRING,
    issued_at: DATE,
    expires_at: DATE,
    credential_id: STRING
})

// Document (CV generado)
(:Document {
    uuid: UUID,
    type: ENUM,                     // cv, cover_letter, portfolio
    format: ENUM,                   // pdf, docx, json_resume
    generated_at: DATETIME,
    template_used: STRING,
    snapshot_ref: STRING            // referencia al Snapshot del universo usado
})
```

### 11.2 Edges

```cypher
// Relaciones principales del dominio
(:Person)-[:HAS_EXPERIENCE {confidence: FLOAT, verified: BOOLEAN}]->(:Experience)
(:Person)-[:HAS_EDUCATION {confidence: FLOAT}]->(:Education)
(:Person)-[:HAS_SKILL {level: ENUM, acquired_at: DATE, source: STRING, confidence: FLOAT}]->(:Skill)
(:Person)-[:SPEAKS {proficiency: ENUM}]->(:Language)
(:Person)-[:HAS_CERTIFICATION {status: ENUM}]->(:Certification)
(:Person)-[:HAS_DOCUMENT]->(:Document)

// Relaciones estructurales
(:Experience)-[:REQUIRED_SKILL {level: ENUM, is_primary: BOOLEAN}]->(:Skill)
(:Experience)-[:WORKED_ON {role: STRING}]->(:Project)
(:Experience)-[:PRECEDED_BY {transition_type: ENUM}]->(:Experience)
(:Education)-[:REQUIRED_SKILL]->(:Skill)

// Anclaje ESCO
(:Skill)-[:ESCO_MATCH {score: FLOAT, match_type: ENUM}]->(:EscoSkill)
(:Experience)-[:ESCO_OCCUPATION_MATCH {score: FLOAT}]->(:EscoOccupation)

// Relaciones ESCO (subgrafo de referencia)
(:EscoSkill)-[:ESCO_BROADER_THAN]->(:EscoSkill)
(:EscoSkill)-[:ESCO_NARROWER_THAN]->(:EscoSkill)
(:EscoSkill)-[:IS_ESSENTIAL_FOR {weight: FLOAT}]->(:EscoOccupation)
(:EscoSkill)-[:IS_OPTIONAL_FOR {weight: FLOAT}]->(:EscoOccupation)
(:EscoSkill)-[:ESCO_RELATED_TO]->(:EscoSkill)
(:EscoSkill)-[:REQUIRES]->(:EscoSkill)          // pre-requisito

// Versionado y provenance
(:Experience)-[:SUPERSEDED_BY {at: DATETIME, reason: STRING}]->(:Experience)
(:Experience)-[:MERGED_INTO {at: DATETIME, reason: STRING}]->(:Experience)
(:Document)-[:GENERATED_FROM {snapshot_id: STRING}]->(:Snapshot)
```

### 11.3 Índices recomendados

```sql
-- PostgreSQL relacional (ya existen o se añaden)
CREATE INDEX idx_experiences_user_id ON experiences(user_id);
CREATE INDEX idx_skills_user_id ON skills(user_id);
CREATE INDEX idx_skills_esco_code ON skills(esco_code) WHERE esco_code IS NOT NULL;

-- pgvector
CREATE INDEX idx_knowledge_embeddings ON knowledge_chunks 
USING hnsw (embedding vector_cosine_ops) WITH (m = 16, ef_construction = 64);

-- Full-text (para BM25)
CREATE INDEX idx_chunks_fts ON knowledge_chunks 
USING gin(to_tsvector('spanish', content));

-- Apache AGE (índices de grafo)
-- Nota: AGE crea índices automáticos sobre properties frecuentemente usadas en MATCH
-- Índices manuales recomendados:
CREATE INDEX idx_age_person_uuid ON graph.person_uuid;  -- vía AGE catalog
CREATE INDEX idx_age_skill_esco ON graph.skill_esco_code;
```

---

## Referencias Clave de la Investigación

1. **Kavas et al. (2025)** — *Multilingual Skill Extraction for Job Vacancy–Job Seeker Matching in Knowledge Graphs* (ACL). Framework de KG con ESCO para matching multilingüe.
2. **CareerPathKG (2026)** — *Knowledge Graph Integrated Framework for Recruitment* (EACL Industry). Career path KG con CV assessment, CV-JD matching, y career guidance.
3. **CAPER (KDD 2025)** — *Enhancing Career Trajectory Prediction using Temporal Knowledge Graph*. TKG para predicción de transiciones laborales con relaciones ternarias.
4. **Gupta & Tadayon (2026)** — *Graphs RAG at Scale: Beyond RAG with LPG and RDF*. Text2Cypher >90% accuracy; LPG supera a RAG2 tradicional.
5. **ESCO + AI** — Comisión Europea (2021). AI para mantener y extender ESCO vía NLP y KG building.
6. **Ontology Learning for ESCO** — *Leveraging LLMs to Navigate the ESCO Taxonomy*. Entity linking y relation classification con LLMs sobre ESCO.
7. **Awesome-GraphMemory (2025-2026)** — Survey completo de graph-based agent memory. Taxonomía: extraction, storage, retrieval.
8. **MERAI (2025)** — *Robust Pipeline for Enterprise-Level Entity Resolution*. Blocking + matching + clustering a escala industrial.
9. **Hybrid Search PostgreSQL** — Jonathan Katz (2024). RRF con pgvector + full-text en PostgreSQL nativo.
10. **Ashpreet Bedi** — Context Providers, Dash v2, Auto-Improving Software. Patrones de plataforma agentic y equipos multi-agente.
