# Informe de Investigación: Arquitecturas Agentic Avanzadas y Sistemas de Referencia

> Fecha: 2026-05-26
> Ámbito: Investigación multidimensional sobre frameworks agentic, RAG avanzado, sistemas de memoria persistente, y plataformas auto-mejorables.
> Objetivo: Extraer mejores prácticas, patrones de diseño y capacidades diferenciadoras para elevar la arquitectura de Universo Profesional.

---

## Tabla de Contenidos

1. [Resumen Ejecutivo](#1-resumen-ejecutivo)
2. [Dimensión 1: Agno Framework — Análisis Profundo](#2-dimensión-1-agno-framework--análisis-profundo)
3. [Dimensión 2: Ashpreet Bedi — Filosofía de Plataformas Agentic](#3-dimensión-2-ashpreet-bedi--filosofía-de-plataformas-agentic)
4. [Dimensión 3: agentmemory — Sistemas de Memoria Persistentes](#4-dimensión-3-agentmemory--sistemas-de-memoria-persistentes)
5. [Dimensión 4: Arquitecturas RAG Avanzadas](#5-dimensión-4-arquitecturas-rag-avanzadas)
6. [Dimensión 5: Patrones de Diseño Agentic](#6-dimensión-5-patrones-de-diseño-agentic)
7. [Dimensión 6: MCP y Protocolos de Integración](#7-dimensión-6-mcp-y-protocolos-de-integración)
8. [Dimensión 7: Sistemas de Memoria para Agentes — Comparativa](#8-dimensión-7-sistemas-de-memoria-para-agentes--comparativa)
9. [Síntesis y Recomendaciones para Universo Profesional](#9-síntesis-y-recomendaciones-para-universo-profesional)
10. [Anexo: URLs y Referencias](#10-anexo-urls-y-referencias)

---

## 1. Resumen Ejecutivo

La investigación abarca siete dimensiones críticas para el diseño de sistemas agentic de próxima generación:

| Dimensión | Hallazgo Clave |
|-----------|----------------|
| **Agno Framework** | Evolución de Phidata a plataforma completa (framework + AgentOS runtime + control plane). Soporta equipos multi-agente, memoria automática/agentic, RAG agentic, evals nativas, MCP/A2A, y workflows durable. |
| **Auto-improving platforms** | Ashpreet Bedi demuestra un ciclo de 5 prompts (Create → Improve → Extend → Hill Climb → Review) que permite a coding agents gestionar plataformas end-to-end. La clave: colocalizar datos, código, logs y evals. |
| **agentmemory** | Motor de memoria de 95.2% R@5 con pipeline de 4 tiers (working → episodic → semantic → procedural), triple retrieval (BM25 + vector + graph), y 53 herramientas MCP. Zero dependencias externas (SQLite + iii-engine). |
| **RAG Avanzado** | Evolución de naive RAG → advanced RAG → agentic RAG → graph RAG → MMA-RAG. Los sistemas líderes usan planificación multi-paso, verificación de evidencia, y recuperación híbrida con reranking. |
| **Patrones Agentic** | ReAct, ReWOO, Reflexion, Evaluator-Optimizer, y Orchestrator-Worker son los 5 patrones dominantes. La tendencia 2025-2026 es hacia agentes especializados que colaboran en vez de monolitos. |
| **MCP** | De facto standard para integración agent-tool. OAuth 2.1 para HTTP transports, separación host/client/server, y observabilidad completa son prácticas obligatorias en producción. |
| **Memoria Comparada** | Mem0 (48K⭐, vector+graph), Letta (21K⭐, OS-tiered), Zep (temporal KG), y agentmemory (coding-specific) representan 4 filosofías distintas. Para coding agents, agentmemory lidera en precisión. |

---

## 2. Dimensión 1: Agno Framework — Análisis Profundo

### 2.1 Visión General

Agno (anteriormente Phidata) se ha transformado de un framework de agents a una **plataforma completa** con tres capas:

1. **Framework**: Construcción de agents, equipos y workflows
2. **AgentOS Runtime**: Servicio FastAPI pre-construido para producción
3. **Control Plane**: UI en os.agno.com para monitorizar y gestionar despliegues

**Estadísticas clave (mayo 2026):**
- ~35K estrellas GitHub
- 100+ toolkits built-in
- 20+ vector databases soportadas
- 23+ model providers
- Soporta MCP y A2A nativamente

### 2.2 Capacidades Diferenciadoras

#### 2.2.1 Agentic RAG (Knowledge)

Agno implementa **Agentic RAG por defecto**: en lugar de inyectar siempre contexto recuperado al prompt (RAG tradicional), el agent decide **si**, **cuándo** y **cómo** buscar en su knowledge base.

```python
# Patrón Agno: el agente controla la recuperación
agent = Agent(
    model=OpenAIChat(id="gpt-4o"),
    knowledge=knowledge_base,
    search_knowledge=True,      # El agente decide cuándo buscar
    read_chat_history=True,     # Puede consultar historial
    show_tool_calls=True,
)
```

**Ventajas sobre RAG tradicional:**
- Menor contaminación de contexto
- El agente puede reformular queries de búsqueda
- Puede decidir que no necesita búsqueda (ahorro de tokens)
- Integración natural con herramientas

#### 2.2.2 Memoria Dual: Automática vs Agentic

Agno ofrece dos modos de memoria **mutuamente excluyentes**:

| Modo | Mecanismo | Caso de Uso |
|------|-----------|-------------|
| **Automática** (`update_memory_on_run=True`) | Agno extrae, almacena y recupera memorias automáticamente tras cada ejecución | Asistentes personales, soporte al cliente |
| **Agentic** (`enable_agentic_memory=True`) | El agente dispone de herramientas para crear/actualizar/eliminar memorias según su criterio | Workflows complejos, multi-turn |

**Modelo de datos de memoria:**
- `memory_id`, `memory`, `topics`, `input`, `user_id`, `agent_id`, `team_id`, `updated_at`
- Almacenamiento en PostgreSQL, SQLite, MongoDB

#### 2.2.3 Teams Multi-Agente

La arquitectura de equipos de Agno soporta tres modos de colaboración:

- **`route`**: El líder enruta cada tarea al agente más adecuado
- **`coordinate`**: El líder delega y coordina resultados intermedios
- **`collaborate`**: Los agentes comparten información abiertamente (brainstorming)

**Observación crítica:** La documentación advierte explícitamente que el mecanismo antiguo de transfer/handoff (2023-2025) **no es escalable** y recomienda la nueva arquitectura de Teams.

#### 2.2.4 Context Providers

Patrón revolucionario introducido por Ashpreet Bedi (ver Sección 3) y adoptado por Agno:

```python
# El agente principal ve solo 2 herramientas por fuente
Agent ↔ ContextProvider ↔ Tools
```

En lugar de exponer 50+ herramientas crudas al agente principal, un `ContextProvider` expone:
- `query_<source>(question)` — lecturas en lenguaje natural
- `update_<source>(instruction)` — escrituras en lenguaje natural

**Beneficios:**
- Supera los 3 muros: contaminación de contexto, scopes borrosos, y lógica de tool-use en el agente principal
- El sub-agente especializado maneja los quirks de cada API
- El agente principal razona sobre *qué* preguntar, no *cómo* usar cada API

#### 2.2.5 Evals Nativas

Tres dimensiones de evaluación:

1. **AccuracyEval**: LLM-as-a-judge con criterios definidos
2. **PerformanceEval**: Latencia, uso de memoria, comparación de configuraciones
3. **ReliabilityEval**: Llamadas a herramientas, manejo de errores, rate limiting

**Patrón de eval:**
```python
evaluation = AccuracyEval(
    model=OpenAIChat(id="o4-mini"),  # Juez
    agent=Agent(...),                  # Agente bajo evaluación
    input="...",
    expected_output="...",
    additional_guidelines="...",
)
```

#### 2.2.6 Workflows Durables

Soporte para workflows de larga duración con:
- `session_state` para cachear resultados intermedios
- Almacenamiento en PostgreSQL/MongoDB/SQLite
- Reanudación tras interrupciones
- HITL (Human-in-the-Loop) a nivel de workflow

#### 2.2.7 Playground / AgentOS UI

Interfaz web para interactuar con agents localmente:
- `serve_playground_app()` levanta FastAPI
- La UI en app.agno.com se conecta al runtime local
- **Ningún dato se envía a agno.com** — todo queda en la BD local
- Soporta múltiples agents, streaming, y visualización de tool calls

### 2.3 Integración MCP en Agno

```python
async with MCPTools(command=f"uvx mcp-server-git") as mcp_tools:
    agent = Agent(
        model=OpenAIChat(id="gpt-4o"),
        tools=[mcp_tools],
    )
    await agent.aprint_response("...", stream=True)
```

**Características:**
- Soporte stdio y HTTP transports
- `MultiMCPTools` para múltiples servidores
- Integración con Playground
- Manejo de cleanup automático via context managers

---

## 3. Dimensión 2: Ashpreet Bedi — Filosofía de Plataformas Agentic

### 3.1 La Plataforma como OS para Agents

Ashpreet Bedi (fundador de Agno) propone que toda plataforma agentic necesita 5 componentes:

1. **Runtime**: Servicio que ejecuta agents (requests, agent loop, streaming, storage, auth)
2. **Storage**: Base de datos para sessions, memory, knowledge, traces, eval history
3. **Connectors**: Herramientas para conectar con sistemas externos (MCP, API, CLI)
4. **Interfaces**: Slack, Discord, Telegram, UIs custom — con identidad unificada cross-surface
5. **Infrastructure**: Docker local, Railway, cloud propio

### 3.2 El Ciclo de Auto-Mejora (5 Prompts)

El diferenciador clave de la filosofía de Bedi es el **ciclo de auto-mejora** gestionado por coding agents:

```
┌─────────┐    ┌──────────┐    ┌─────────┐    ┌───────────┐    ┌─────────┐
│ Create  │───▶│ Improve  │───▶│ Extend  │───▶│ Hill Climb│───▶│ Review  │
└─────────┘    └──────────┘    └─────────┘    └───────────┘    └─────────┘
     │                                                    │
     └──────────────────── loop ──────────────────────────┘
```

| Prompt | Función | Input | Output |
|--------|---------|-------|--------|
| **Create** | Scaffold de nuevo agente | Descripción de tarea + herramientas necesarias | Archivo de agente registrado + smoke test |
| **Improve** | Endurecer agente contra su propia spec | Lectura de INSTRUCTIONS | 8-12 probes (golden path, edge cases, adversarial) + fixes |
| **Extend** | Añadir capacidades | Descripción del cambio | Cambio quirúrgico + smoke test |
| **Hill Climb** | Mejora recursiva vía evals | Eval suite completa | Diagnóstico de fallos + fixes + re-run |
| **Review** | Sincronizar docs/código/config | Repo completo | Fixes mecánicos + flags de drift mayor |

### 3.3 Context Providers — El Patrón Clave

El artículo más influyente es "Context Providers" (ashpreetbedi.com/context-providers), que identifica los **tres muros** de los agentes con múltiples herramientas:

**Muro 1 — Contaminación de contexto:** Cada herramienta ocupa tokens preciosos. 50+ herramientas = el modelo alucina herramientas inexistentes.

**Muro 2 — Scopes borrosos:** Dos herramientas llamadas `search` o `workspace` collisionan semánticamente.

**Muro 3 — Lógica de tool-use en el agente principal:** El prompt del agente principal se convierte en la unión de todos los quirks de cada API.

**Solución — ContextProvider:**

```python
slack = SlackContextProvider(id="slack", token=..., model=provider_model)
drive = GDriveContextProvider(id="drive", service_account_file=..., model=provider_model)
crm = DatabaseContextProvider(id="crm", sql_engine=engine, model=provider_model)

agent = Agent(
    model=OpenAIResponses(id="gpt-5.4"),
    tools=[*slack.get_tools(), *drive.get_tools(), *crm.get_tools()],
    instructions="\n".join([slack.instructions(), drive.instructions(), crm.instructions()]),
)
```

**Resultado:** El agente principal ve 4 herramientas en lugar de 50+. Los sub-agentes especializados manejan los detalles de cada fuente.

### 3.4 Dash v2 — Sistema de Datos Auto-Aprendizaje

Dash es un sistema de datos open-source con **3 agentes especializados**:

| Agente | Rol | Capacidades | Restricciones |
|--------|-----|-------------|---------------|
| **Leader** | Rutear y sintetizar | Decide quién responde, sintetiza respuestas | Sin herramientas SQL |
| **Analyst** | Escribir y ejecutar SQL | Genera insights a partir de datos | Read-only por configuración de PostgreSQL (`default_transaction_read_only=on`) |
| **Engineer** | Construir infraestructura | Crea views, tablas resumen, datos computados | Solo puede escribir en schema `dash` (bloqueado por SQLAlchemy event listener) |

**Loop de auto-aprendizaje:**
1. Usuario pregunta → Leader delega
2. Analyst busca knowledge → escribe SQL correcto → devuelve insight
3. Queries correctas se guardan en knowledge; errores se convierten en learnings
4. Patrones repetidos → Engineer construye views → registra en knowledge base
5. Próxima vez: Analyst usa la view directamente

**Seguridad por diseño:**
- Dos schemas con frontera dura: `public` (datos empresa, solo lectura) y `dash` (infraestructura, escritura)
- El Analyst es read-only porque la **base de datos misma** rechaza escrituras, no porque el prompt lo diga
- El Engineer solo puede escribir en `dash` — protección a nivel de sistema

### 3.5 Auto-Improving Software

El principio fundamental: **"It works because we control the stack"**

Tres condiciones necesarias:
1. **Cada acción expuesta como API**: running an agent, reading a session, running an eval
2. **Datos colocalizados**: Sessions y traces en PostgreSQL; el coding agent puede leer sin salir de su entorno
3. **Logs over everything**: La plataforma corre localmente en Docker; el loop test→review es ~5s

---

## 4. Dimensión 3: agentmemory — Sistemas de Memoria Persistentes

### 4.1 Arquitectura

agentmemory es un motor de memoria persistente para coding agents (Claude Code, Cursor, Codex, etc.), construido sobre **iii-engine** (tres primitivas: Worker/Function/Trigger).

**Estadísticas (v0.9.22):**
- 95.2% R@5 en LongMemEval-S (ICLR 2025)
- 92% reducción de tokens vs full-context
- 53 herramientas MCP
- 12 hooks de auto-captura
- 950+ tests
- 0 dependencias de base de datos externas (SQLite + iii-engine)

### 4.2 Pipeline de Memoria

```
PostToolUse hook dispara
  → SHA-256 dedup (ventana 5min)
  → Privacy filter (strip secrets, API keys)
  → Almacenar observación raw
  → LLM compress → structured facts + concepts + narrative
  → Vector embedding (6 providers + local)
  → Indexar en BM25 + vector

Stop / SessionEnd hook dispara
  → Resumir sesión
  → Knowledge graph extraction (opcional)
  → Slot reflection (opcional)

SessionStart hook dispara
  → Cargar perfil de proyecto (top concepts, files, patterns)
  → Hybrid search (BM25 + vector + graph)
  → Budget de tokens (default: 2000)
  → Inyectar en conversación
```

### 4.3 Consolidación de 4 Tiers

Inspirada en el cerebro humano:

| Tier | Qué | Analogía |
|------|-----|----------|
| **Working** | Observaciones raw de tool use | Memoria a corto plazo |
| **Episodic** | Resúmenes comprimidos de sesiones | "Qué pasó" |
| **Semantic** | Hechos y patrones extraídos | "Qué sé" |
| **Procedural** | Workflows y patrones de decisión | "Cómo hacerlo" |

Las memorias decaen con el tiempo (curva de Ebbinghaus). Las frecuentemente accedidas se fortalecen. Las obsoletas se evictan automáticamente.

### 4.4 Triple Retrieval

| Stream | Qué hace | Cuándo |
|--------|----------|--------|
| **BM25** | Keyword matching con stemmer y synonym expansion | Siempre |
| **Vector** | Cosine similarity sobre embeddings densos | Cuando hay embedding provider |
| **Graph** | Traversal del knowledge graph via entity matching | Cuando se detectan entidades en la query |

Fusión con **Reciprocal Rank Fusion (RRF, k=60)** y diversificación por sesión (max 3 resultados por sesión).

### 4.5 Hooks de Auto-Captura

| Hook | Captura |
|------|---------|
| `SessionStart` | Project path, session ID |
| `UserPromptSubmit` | User prompts (privacy-filtered) |
| `PreToolUse` | File access patterns + context enriquecido |
| `PostToolUse` | Tool name, input, output |
| `PostToolUseFailure` | Error context |
| `PreCompact` | Re-inyección de memoria antes de compactación |
| `SubagentStart/Stop` | Lifecycle de sub-agentes |
| `Stop` | Resumen end-of-session |
| `SessionEnd` | Marcador de sesión completa |

### 4.6 Comparativa vs Competidores

| Característica | agentmemory | mem0 | Letta/MemGPT | Built-in (CLAUDE.md) |
|----------------|-------------|------|--------------|---------------------|
| Tipo | Memory engine + MCP server | Memory layer API | Full agent runtime | Static file |
| R@5 retrieval | **95.2%** | 68.5% (LoCoMo) | 83.2% (LoCoMo) | N/A |
| Auto-capture | 12 hooks (zero effort) | Manual `add()` | Agent self-edits | Manual editing |
| Búsqueda | BM25 + Vector + Graph (RRF) | Vector + Graph | Vector (archival) | Carga todo al contexto |
| Multi-agent | MCP + REST + leases + signals | API (no coordination) | Within Letta only | Per-agent files |
| Lock-in | Ninguno (any MCP client) | Ninguno | Alto (must use Letta) | Per-agent format |
| Dependencias | Ninguna (SQLite + iii) | Qdrant / pgvector | Postgres + vector DB | Ninguna |
| Lifecycle | 4-tier + decay + auto-forget | Passive extraction | Agent-managed | Manual pruning |
| Eficiencia tokens | ~1,900 tokens/session | Variable | Core memory in context | 22K+ tokens |
| Viewer real-time | Sí (port 3113) | Cloud dashboard | Cloud dashboard | No |

### 4.7 Lecciones Arquitectónicas

1. **Zero external DBs**: Usar SQLite local + iii-engine elimina toda la complejidad operacional
2. **Privacy-first**: Strip secrets antes de almacenar — nunca confiar en que el agente no loguee tokens
3. **Content-addressable dedup**: SHA-256 de observaciones evita duplicados sin complejidad
4. **Multi-strategy retrieval**: Ninguna estrategia sola es suficiente; la fusión es obligatoria
5. **Hooks, no APIs**: Captura pasiva via hooks es superior a requerir llamadas manuales `memory.add()`

---

## 5. Dimensión 4: Arquitecturas RAG Avanzadas

### 5.1 Taxonomía de RAG (2025-2026)

```
RAG Evolutivo:
├── Naive RAG (2020-2022)
│   └── Embed → Retrieve → Generate
├── Advanced RAG (2023-2024)
│   ├── Query rewriting / expansion
│   ├── Hybrid search (vector + BM25)
│   ├── Reranking
│   └── Parent-child chunking
├── Modular RAG (2024)
│   └── Módulos intercambiables: retrieve, rerank, generate
├── Agentic RAG (2025)
│   ├── Plan → Route → Act → Verify → Stop
│   ├── Multi-hop reasoning
│   ├── Self-RAG (el modelo decide si recuperar)
│   └── Corrective RAG (re-recuperar si evidencia débil)
├── Graph RAG (2024-2025)
│   ├── Knowledge graphs para relaciones
│   └── Multi-hop traversal
└── MMA-RAG (2026)
    └── Multimodal + Agentic + Graph combinados
```

### 5.2 Agentic RAG

El paradigma dominante en 2025-2026. Características:

1. **Planificación**: El agente descompone la pregunta en sub-preguntas
2. **Ruteo**: Cada sub-pregunta va al retriever adecuado (graph/Cypher para relaciones, hybrid para fechas/facts)
3. **Ejecución**: Recuperar evidencia con provenance
4. **Verificación**: ¿Cada sub-meta tiene evidencia fuerte? ¿Hay conflictos?
5. **Parada**: Cuando todas las sub-metas están satisfechas o se agota el budget

### 5.3 Self-RAG, Corrective RAG, Adaptive RAG

| Técnica | Mecanismo | Cuándo usar |
|---------|-----------|-------------|
| **Self-RAG** | El LLM aprende *cuándo* necesita recuperar. Puede decidir que la query es simple y responder sin búsqueda. | Cuando muchas queries no necesitan contexto externo |
| **Corrective RAG (C-RAG)** | Evalúa calidad de documentos recuperados. Si son irrelevantes, dispara nueva búsqueda. | Cuando la calidad del corpus es variable |
| **Adaptive RAG (A-RAG)** | Adapta estrategia según la query: múltiples fuentes, multi-step, o fallback a LLM puro. | Cuando las queries son heterogéneas en complejidad |
| **Graph RAG** | Modela entidades y relaciones en grafo. Recupera paths, no solo passages. | Datos con relaciones complejas (organizaciones, legal, científico) |

### 5.4 Los 10 Mandamientos del RAG en Producción

1. Evaluar primero, optimizar después
2. Calidad de chunks > modelo de embeddings
3. Siempre reranker en producción
4. Filtrar en retrieval, no en generación
5. Mismo modelo para index y query
6. Responder "No lo sé" cuando hay incertidumbre
7. Monitorizar continuamente
8. Cachear lo posible (ahorro 20-40%)
9. Testear con queries reales de usuarios
10. Empezar simple, añadir complejidad solo cuando el eval lo demande

### 5.5 Técnicas Avanzadas Específicas

**Hybrid Search + RRF:**
- Combinar BM25 (exact tokens) + vector (semántica)
- Fusión con Reciprocal Rank Fusion (k=60)
- Agno soporta esto nativamente en PgVector, LanceDB, Pinecone

**Agentic Chunking:**
- En lugar de chunks de tamaño fijo, el agente decide cómo dividir documentos
- Preserva estructura semántica y relaciones lógicas

**Query Expansion / HyDE:**
- Generar hipotéticos documentos/respuestas para mejorar recall
- Puentea gaps de phrasing entre query y documentos

**Parent-Document Retrieval:**
- Indexar chunks pequeños para precisión
- Recuperar el documento padre completo para contexto

---

## 6. Dimensión 5: Patrones de Diseño Agentic

### 6.1 Los 9 Patrones Dominantes

| # | Patrón | Descripción | Caso de Uso |
|---|--------|-------------|-------------|
| 1 | **Prompt Chaining** | Output de un LLM = input del siguiente | Conversaciones multi-turn, pipelines secuenciales |
| 2 | **Plan and Execute** | Planificar → Ejecutar → Revisar → Ajustar | Automatización de procesos de negocio |
| 3 | **Parallelization** | Dividir tarea en subtareas independientes concurrentes | Code review, evaluación de candidatos, A/B testing |
| 4 | **Orchestrator-Worker** | Orchestrator descompone, workers especializados ejecutan, orchestrator sintetiza | RAG complejo, coding agents, research multi-modal |
| 5 | **Routing** | Clasificar input y enrutar al agente especializado | Soporte multi-dominio, sistemas de debate |
| 6 | **Evaluator-Optimizer** | Generar → Evaluar → Mejorar → Iterar | Coding iterativo, diseño feedback-driven |
| 7 | **Reflection** | Auto-revisar performance tras cada ejecución | Agents que aprenden de errores |
| 8 | **ReWOO** | Plan completo primero, luego ejecución paralela, luego síntesis | ETL, procesamiento batch, extracción documental |
| 9 | **Autonomous Workflow** | Loop continuo: tool feedback → self-improvement | Evaluaciones autónomas, guardrails dinámicos |

### 6.2 ReAct vs ReWOO

**ReAct (Reason + Act):**
```
Thought → Action (API/tool) → Observation → Next Thought → ...
```
- Pros: Adaptativo, exploratorio, trazable
- Contras: Riesgo de loops infinitos, cascadas de fallos, coste de tokens por iteración

**ReWOO (Reasoning Without Observation):**
```
Plan → Execute (parallel) → Summarize
```
- Pros: Eficiente, determinista, bajo coste
- Contras: No se auto-corrige mid-ejecución, fragilidad del planner

**Recomendación híbrida:** Usar ReWOO para workflows conocidos/repetibles, con fallback a ReAct cuando el plan falla.

### 6.3 CodeAct

El agente usa **código como lenguaje de razonamiento** en lugar de natural language:

```
Thought → Generate Code → Execute → Observe → Continue
```

- Reduce ambigüedad del razonamiento
- Permite ejecución en sandbox
- Ideal para tareas matemáticas, data analysis, transformaciones complejas

### 6.4 Tendencias 2025-2026

1. **Especialización > Generalización**: Swarms de agentes estrechos que colaboran en vez de monolitos
2. **Self-healing**: Detección y resolución autónoma de problemas
3. **Graph-of-thoughts**: Planificación con estructuras de grafo en lugar de secuencias lineales
4. **Role guardrails**: Límites estrictos por rol de agente
5. **Eval-driven development**: Los evals son los tests unitarios de los agents

---

## 7. Dimensión 6: MCP y Protocolos de Integración

### 7.1 Estado del MCP (2026)

MCP se ha convertido en el **de facto standard** para integración agent-tool. El mercado de MCP servers se proyecta en **$10.4B para 2026** (24.7% CAGR).

**Características clave:**
- JSON-RPC sobre stdio o HTTP (SSE)
- Descubrimiento dinámico de herramientas
- Contexto estructurado bidireccional
- 1200+ servidores MCP open-source

### 7.2 Best Practices para MCP en Producción

1. **OAuth 2.1 para HTTP transports** — reemplaza API keys y auth custom
2. **Separación host/client/server** — cada uno con responsabilidades claras
3. **RBAC y least-privilege** — read-only vs write diferenciado por herramienta
4. **Consentimiento explícito del usuario** antes de acciones sensibles
5. **Logging estructurado** de todas las transacciones MCP
6. **Manejo de sesiones** con reconnection y resume
7. **Validación de schemas** en tool calls
8. **Rate limiting** por herramienta y por sesión

### 7.3 Seguridad MCP (NSA Advisory)

La NSA ha publicado consideraciones de seguridad para MCP:

- **Prompt injection** via tool parameters
- **Parasitic toolchain attacks** — servidores MCP maliciosos
- **Token passthrough** — riesgo de exfiltración de credenciales
- **Deserialización insegura** en payloads MCP

**Mitigaciones:**
- Sandboxing de servidores MCP
- Validación estricta de inputs/outputs
- Network segmentation
- Auditoría continua

### 7.4 Context Providers como Evolución de MCP

Ashpreet Bedi propone que MCP soluciona la *interoperabilidad* pero no los *tres muros* del agente principal. Los Context Providers son una capa sobre MCP que:

- Colapsa un servidor MCP de 50 herramientas a 2 (`query_source`, `update_source`)
- Aísla los quirks de cada API en sub-agentes especializados
- Permite caching por sesión dentro del provider
- Soporta autenticación per-user que sobrevive el hop

---

## 8. Dimensión 7: Sistemas de Memoria para Agentes — Comparativa

### 8.1 Taxonomía de Memoria

| Sistema | Clase | Arquitectura | Open Source | Stars | Diferenciador |
|---------|-------|-------------|-------------|-------|---------------|
| **Mem0** | Personalización + Institucional | Vector + Graph | Apache 2.0 | ~48K | Mayor ecosistema, integración en 3 líneas |
| **Letta** | Ambas | Tiered (OS-inspired) | Apache 2.0 | ~21K | Agentes gestionan su propia memoria |
| **Zep / Graphiti** | Ambas (temporal) | Temporal KG | Graphiti: open | ~24K | Tracking temporal de cambios de hechos |
| **Cognee** | Institucional | KG + Vector | Open core | ~12K | 30+ conectores, extracción de grafo |
| **agentmemory** | Coding agents | BM25 + Vector + Graph (RRF) | Apache 2.0 | Creciendo rápido | 95.2% R@5, zero-config, MCP nativo |
| **Hindsight** | Institucional | Multi-strategy hybrid | MIT | ~4K | 4 estrategias paralelas de retrieval |
| **LangMem** | Personalización | Flat KV + vector | MIT | ~1.3K | Integración profunda con LangGraph |

### 8.2 Dimensiones de Comparación

**Vector-first** (LangMem, SuperMemory):
- Retrieval por similitud, más simple de razonar
- Principalmente personalización

**Tiered / agent-managed** (Letta):
- Jerarquía tipo OS: working memory vs archival
- El agente controla qué permanece en contexto

**Vector + Graph** (Mem0, Zep, Cognee):
- Relaciones entre entidades + conocimiento estructurado
- Mem0 gatea graph features detrás de Pro

**Multi-strategy retrieval** (Hindsight, agentmemory):
- Varios métodos en paralelo con reranking
- Captura lo que los sistemas single-strategy pierden

### 8.3 Recomendación por Caso de Uso

| Si necesitas... | Considerar |
|-----------------|------------|
| Mayor ecosistema y comunidad | Mem0 |
| Agentes que gestionan su propio contexto | Letta |
| Tracking temporal de hechos ("vivía en X, ahora en Y") | Zep / Graphiti |
| Knowledge graph + ingestión multimodal | Cognee |
| Coding agents con máxima precisión de recall | agentmemory |
| Highest benchmark scores en institutional knowledge | Hindsight |
| Ya usas LangGraph y quieres memory simple | LangMem |

---

## 9. Síntesis y Recomendaciones para Universo Profesional

### 9.1 Gap Analysis — Estado Actual vs Estado Deseado

| Área | Estado Actual (MVP) | Estado Deseado | Prioridad |
|------|---------------------|----------------|-----------|
| **RAG** | Mock básico con embeddings sha256 | Agentic RAG híbrido (BM25 + vector + graph) | Alta |
| **Memoria** | Single chat por usuario, ventana 40 msgs | Memoria persistente multi-tier con auto-consolidación | Alta |
| **Multi-agent** | Agentes Agno individuales | Teams especializados (Coordinator pattern) | Media-Alta |
| **MCP** | Servidor MCP propio con OAuth 2.1 | Context Providers sobre MCP para aislar complejidad | Media |
| **Evals** | Pytest con cobertura 40% | Evals nativas de Agno + suite de regression agentic | Media |
| **Auto-mejora** | Manual | Loop de hill-climb contra eval suite | Baja-Media |
| **HITL** | Cards en frontend para confirmación | HITL integrado en workflows con pausas estructuradas | Media |
| **Observabilidad** | structlog + Prometheus + OpenTelemetry | Trace waterfall por agent run, eval history en DB | Media |

### 9.2 Recomendaciones Arquitectónicas Específicas

#### RAG-1: Migrar a Agentic RAG Híbrido

**Propuesta:** Reemplazar el pipeline RAG mockeado actual con una arquitectura agentic híbrida:

```
Usuario
  │
  ▼
[Agente Principal — Universo Chat]
  │
  ├──▶ [ContextProvider: Knowledge Base] — query_knowledge(question)
  │       └── Sub-agente con PgVector + BM25 + Graph (AGE)
  │
  ├──▶ [ContextProvider: Universe Data] — query_universe(question)  
  │       └── Sub-agente con acceso read-only a PostgreSQL
  │
  └──▶ [ContextProvider: Documents] — query_documents(question)
          └── Sub-agente con acceso a filesystem/S3
```

**Implementación:**
- Usar `search_knowledge=True` en Agno para RAG agentic
- Configurar `PgVector` con `SearchType.hybrid` (ya soportado por Agno)
- Integrar Apache AGE para Graph RAG sobre la ontología ESCO
- Implementar reranking con Cohere Reranker o similar

#### MEM-1: Implementar Memoria Persistent de 2 Niveles

**Nivel 1 — Session Memory (corto plazo):**
- Usar `storage=PostgresAgentStorage` de Agno para persistir historial
- `add_history_to_messages=True` con `num_history_responses` dinámico

**Nivel 2 — User Memory (largo plazo):**
- Activar `update_memory_on_run=True` para extracción automática
- O usar `enable_agentic_memory=True` para control del agente
- Almacenar en PostgreSQL (ya tenemos pgvector)

**Nivel 3 — Institutional Memory (conocimiento del dominio):**
- Knowledge base con validaciones de queries SQL frecuentes
- Business rules del dominio CV/profesional
- Learnings acumulados de correcciones de usuarios

#### AGT-1: Crear Equipo Especializado de 3 Agentes

Inspirado en Dash v2, proponemos:

| Agente | Rol | Herramientas | Restricciones |
|--------|-----|--------------|---------------|
| **Universe Assistant** (Líder) | Entender intención, rutear, sintetizar | Ninguna DB directa | Solo orquestación |
| **Data Analyst** | Consultar universe, generar insights | PostgreSQL read-only | `default_transaction_read_only=on` |
| **Document Engineer** | Generar/modificar CVs, cover letters | Jinja2, WeasyPrint, python-docx | Solo schema `documents` |
| **Coherence Guardian** | Validar merges, detectar conflictos | Reglas declarativas de merge | Solo validación, no escritura |

#### MCP-1: Evolucionar Servidor MCP con Context Providers

**Estado actual:** Servidor MCP propio con OAuth 2.1 + PKCE + DCR, tools para CRUD del universo.

**Evolución propuesta:**
1. Mantener el servidor MCP como infraestructura de conexión
2. Añadir una capa de `ContextProvider` que exponga:
   - `query_universe(question)` — sub-agente con acceso a universe data
   - `update_universe(instruction)` — sub-agente con motor de coherencia
   - `generate_document(instruction)` — sub-agente con templates Jinja2
3. El agente principal (Claude Code, Cursor, etc.) ve 3 herramientas en lugar de 20+

#### EVAL-1: Implementar Eval Suite de Agno

**Categorías de evals:**

1. **Accuracy:**
   - ¿El agente extrae correctamente entidades del CV?
   - ¿El merge de coherencia preserva semántica?
   - ¿La generación de documentos respeta el formato?

2. **Reliability:**
   - ¿El agente llama las herramientas correctas?
   - ¿Maneja errores de forma graceful?
   - ¿Respeta rate limits?

3. **Performance:**
   - Latencia de generación de CV
   - Tiempo de consulta al grafo
   - Uso de tokens por interacción

**Implementación:**
```python
# evals/cases.py
from agno.eval.accuracy import AccuracyEval, AccuracyResult
from agno.eval.reliability import ReliabilityEval

evals = [
    AccuracyEval(
        name="extract_education",
        agent=universe_agent,
        input="Añade mi máster en IA por la UPM (2023-2025)",
        expected_output_contains="UPM, Master, 2023, 2025",
        criteria="La respuesta confirma extracción correcta de institución, título, y fechas",
    ),
    ReliabilityEval(
        name="coherence_merge",
        agent=coherence_agent,
        input="Merge de experiencia duplicada",
        expected_tool_calls=("upsert_experience",),
    ),
]
```

#### INF-1: Pipeline de Auto-Mejora (Fase 2)

**Fase 1 (inmediata):** Evals manuales en CI
**Fase 2 (futura):** Hill-climb automatizado

Para Fase 2, necesitamos:
1. Colocalizar evals, traces, y código en el mismo repo
2. Exponer cada eval como endpoint API ejecutable
3. Logging estructurado de todos los agent runs
4. Script de hill-climb que: corre evals → diagnostica fallos → edita prompts → re-corre

### 9.3 Roadmap Sugerido

| Fase | Timeline | Entregables |
|------|----------|-------------|
| **Fase 0: Fundación** | 2 semanas | Upgrade Agno a 2.6.9+, implementar Agentic RAG híbrido con PgVector |
| **Fase 1: Memoria** | 2 semanas | Persistent storage para sessions, user memory con `update_memory_on_run`, knowledge base curada |
| **Fase 2: Teams** | 3 semanas | Refactor a 3-agent team (Leader, Analyst, Engineer), implementar Context Providers |
| **Fase 3: Evals** | 2 semanas | Suite de evals (accuracy, reliability, performance), integración en CI |
| **Fase 4: MCP v2** | 2 semanas | Evolucionar servidor MCP a Context Provider pattern, reducir tool surface |
| **Fase 5: Auto-mejor** | Continuo | Hill-climb loop, scheduled eval runs, drift detection docs/código |

### 9.4 Cambios en Dependencias

| Acción | Dependencia | Notas |
|--------|-------------|-------|
| **Upgrade** | `agno>=2.6.9` | Teams, Context Providers, Evals, Agentic Memory |
| **Añadir** | `pgvector` (ya existe) + hybrid search config | Configurar BM25 en PostgreSQL o usar RRF manual |
| **Añadir** | `cohere` reranker (opcional) | Para reranking de retrieval results |
| **Evaluar** | `agentmemory` MCP | Para desarrollo local con Claude Code/Cursor |
| **Revisar** | `mcp>=1.1.0` | Verificar compatibilidad con Context Provider pattern |

---

## 10. Anexo: URLs y Referencias

### Agno Framework
- Documentación: https://docs.agno.com/
- Índice completo: https://docs.agno.com/llms.txt
- GitHub releases: https://github.com/agno-agi/agno/releases
- GitHub repo: https://github.com/agno-agi/agno

### Ashpreet Bedi Blog
- Agent Platform Build Itself: https://www.ashpreetbedi.com/agent-platform-build-itself
- Auto-Improving Software: https://www.ashpreetbedi.com/auto-improving-software
- Agent Platform: https://www.ashpreetbedi.com/agent-platform
- Context Providers: https://www.ashpreetbedi.com/context-providers
- Dash v2: https://www.ashpreetbedi.com/dash-v2

### agentmemory
- GitHub: https://github.com/rohitg00/agentmemory
- npm: https://www.npmjs.com/package/@agentmemory/agentmemory
- Benchmarks: https://github.com/rohitg00/agentmemory/blob/main/benchmark/COMPARISON.md

### RAG y Agentic Design
- RAG Production Guide: https://gist.github.com/1kalin/ab7dff1afd6821cf20404c9fea7a0c07
- Advanced RAG Techniques (Neo4j): https://neo4j.com/blog/genai/advanced-rag-techniques/
- Agentic RAG Survey: https://arxiv.org/pdf/2602.19127
- MMA-RAG: https://hal.science/hal-05322313v1/file/MMA_RAG_preprint.pdf
- Graph RAG: https://www.emergentmind.com/topics/graph-based-rag

### Patrones Agentic
- 9 Workflow Patterns: https://www.marktechpost.com/2025/08/09/9-agentic-ai-workflow-patterns-transforming-ai-agents-in-2025/
- Designing Systems of Agents: https://lanternstudios.com/insights/blog/agentic-architectures-designing-systems-of-ai-agents-that-actually-work/
- Agentic Design Patterns: https://levelup.gitconnected.com/agentic-design-patterns-what-they-actually-are-beyond-the-textbooks-fa3eebd01ed8

### Evals y Auto-Mejora
- Self-Evolving Agents (OpenAI): https://developers.openai.com/cookbook/examples/partners/self_evolving_agents/autonomous_agent_retraining
- EDDOps Process Model: https://arxiv.org/html/2411.13768v3
- Better Ways to Build Self-Improving Agents: https://yoheinakajima.com/better-ways-to-build-self-improving-ai-agents/

### MCP
- MCP Spec: https://modelcontextprotocol.io/specification/
- NSA MCP Security: https://www.nsa.gov/Portals/75/documents/Cybersecurity/CSI_MCP_SECURITY.pdf
- MCP Best Practices: https://www.cdata.com/blog/mcp-server-best-practices-2026
- MCP Use Cases: https://obot.ai/resources/learning-center/model-context-protocol-use-cases/

### Memoria Comparada
- Best AI Agent Memory Systems: https://vectorize.io/articles/best-ai-agent-memory-systems
- Agent Memory Survey: https://www.graphlit.com/blog/survey-of-ai-agent-memory-frameworks
- Letta vs Mem0 vs Zep: https://forum.letta.com/t/agent-memory-letta-vs-mem0-vs-zep-vs-cognee/88
- Memory in the Age of AI Agents (arXiv): https://arxiv.org/html/2603.04740v1
