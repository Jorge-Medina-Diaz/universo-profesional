# Universo Profesional — Guía para Agentes de Código

> Este fichero está escrito para agentes de IA que necesiten entender, modificar o ampliar el proyecto sin conocimiento previo. La información se basa únicamente en el estado real del repositorio; no se asumen generalizaciones.

---

## 1. Resumen del proyecto

**Universo Profesional** es un SaaS B2C español (MVP) que sustituye al "CV en Word" por un **Universo Profesional** versionado: un grafo de conocimiento estructurado y vivo sobre la trayectoria de una persona. El diferenciador clave es un **servidor MCP remoto** (OAuth 2.1 + PKCE + DCR) que permite actualizar el perfil y generar CVs en lenguaje natural desde agentes de IA como Claude Code, Codex o Cursor.

**Estado actual:** MVP local. Todas las integraciones externas tienen implementaciones mock; no se necesitan credenciales para arrancar el stack completo.

**Licencia:** AGPL-3.0-only (backend).

---

## 2. Stack tecnológico

### Backend (`backend/`)
- **Lenguaje:** Python 3.13+
- **Framework:** FastAPI 0.115 + Uvicorn (ASGI)
- **Validación:** Pydantic v2 + pydantic-settings
- **Base de datos:** PostgreSQL 16 + pgvector 0.8 + Apache AGE (asyncpg en runtime, psycopg v3 en Alembic)
- **Migraciones:** Alembic
- **Cola:** arq sobre Redis 7
- **Agentes/IA:** Agno ≥2.6.7 + AG-UI protocol + Anthropic/OpenAI SDKs
- **Auth:** JWT RS256 (python-jose), Argon2, Authlib, pyOTP (2FA), OAuth 2.1 AS propio
- **Documentos:** WeasyPrint (PDF), python-docx, Jinja2
- **Grafo/Recuperación:** python-igraph (PageRank), scikit-learn (PCA, outlier detection)
- **Similitud textual:** `jellyfish` (Jaro-Winkler, phonetic) para entity resolution y ESCO cross-encoder
- **Observabilidad:** structlog, Prometheus client, OpenTelemetry (FastAPI + SQLAlchemy), Sentry
- **Rate limiting:** slowapi + limits[redis]
- **Email:** aiosmtplib (mock/MailHog en dev; Brevo/Postmark en prod)
- **MCP:** SDK oficial Python `mcp>=1.1.0` (transporte HTTP streamable)
- **Gestor de dependencias:** `uv` (usado en Docker; build system Hatchling)

### Frontend (`frontend/`)
- **Framework:** React 19 (StrictMode)
- **Lenguaje:** TypeScript 5.6 (strict, `noUnusedLocals`, `noUnusedParameters`)
- **Bundler:** Vite 5.4
- **Estilos:** Tailwind CSS 3.4 + CSS custom properties (diseño Pirsch-inspired)
- **Router:** Hash-based custom router propio (`src/app/Router.tsx`) con `React.lazy` para code splitting
- **Estado:** Zustand 5 (auth), TanStack Query 5 (server state), React Hook Form 7 (formularios)
- **Chat/Agentes:** CopilotKit v1.57 (`@copilotkit/react-core`, `react-ui`, `runtime-client-gql`)
- **Grafo visual:** Sigma.js 3 + `@react-sigma/core`, Graphology + forceatlas2
- **Animación:** Motion (ex-Framer Motion) v12
- **i18n:** i18next + react-i18next + browser language detector
- **Tipografía:** DM Sans (cuerpo) + Fraunces Variable (display), auto-alojadas vía `@fontsource` (sin Google Fonts)
- **Iconos:** Lucide React
- **Testing:** Vitest 2.1 + jsdom + `@testing-library/react`
- **Linting:** ESLint 9 + `@typescript-eslint` + `react` + `react-hooks`

---

## 3. Estructura del código

### Backend — Arquitectura Limpia / DDD por contextos acotados

Cada contexto acotado bajo `backend/src/` sigue la regla de dependencias:

```
domain/ → application/ → infrastructure/ → interfaces/
```

Esta regla está **forzada por `import-linter`** (configurado en `pyproject.toml` y en `backend/.importlinter`).

**Contextos acotados (`backend/src/`):**

| Contexto | Responsabilidad |
|----------|-----------------|
| `shared/` | Kernel transversal: DB, config, logging, seguridad, eventos, worker, rate-limit, embeddings |
| `identity/` | Registro, login, JWT, OAuth, 2FA, RGPD export/delete |
| `universe/` | El "Universo Profesional" (educations, experiences, projects, skills, etc.) — núcleo del producto |
| `documents/` | Generación de CVs/cover letters, almacenamiento, compartir |
| `ai_generation/` | Pipeline RAG (mockeado en MVP): parse JD → embed → retrieve → rerank → LLM → JSON Resume → PDF/DOCX |
| `billing/` | Cuotas, suscripciones, Stripe (mock/real) |
| `agents/` | Agentes Agno, 28 especialistas, herramientas, flujos de trabajo, memoria, context providers, auto-enrichment |
| `coherence/` | Motor de coherencia: cada escritura pasa por upsert con reglas de merge declarativas |
| `graph/` | Apache AGE + ontología ESCO (Sprint M en adelante) |
| `knowledge/` | RAG / base de conocimiento (chunks en pgvector) |
| `notes/` | Notas del usuario (markdown + tags) |
| `integrations/` | LinkedIn, GitHub OAuth, Bright Data |
| `mcp_server/` | Servidor MCP: OAuth 2.1 AS (RFC 8414, 9728, 8707, 7591) + tools MCP |
| `rubrics/` | Rúbricas / documentos de evaluación |

**Otros directorios clave del backend:**
- `backend/alembic/` — Migraciones Alembic (async-aware `env.py`, usa `psycopg` sync)
- `backend/templates/` — Plantillas Jinja2 para CVs
- `backend/tests/{unit,integration,e2e}/` — Tests por categoría
- `backend/scripts/` — Scripts auxiliares (benchmarks, ingestión ESCO, migraciones legacy)

**Subdirectorios nuevos del backend (post-Sprint R):**

| Ruta | Responsabilidad |
|------|-----------------|
| `src/agents/context_providers/` | Inyección de contexto por intent (`universe_provider`, `document_provider`, base, router) |
| `src/agents/infrastructure/` | Proposal store HITL, sanitizers Anthropic, adaptadores de infraestructura |
| `src/agents/memory/` | Sliding window digest, memoria estructurada (semantic/procedural/episodic), self-learning loop |
| `src/agents/tools/` | ~20 ficheros de herramientas: reads, writes, discovery, document, graph query, learning, retrieval, UI widgets |
| `src/agents/workflows/` | Flujos programados: `curator.py`, `universe_enrichment.py` |
| `src/graph/application/cross_encoder.py` | `FeatureReranker` — reranking de candidatos ESCO con Jaro-Winkler + Jaccard |
| `src/graph/domain/esco_types.py` | Tipos de datos del linker ESCO (`EscoCandidate`, `EscoLinkResult`, `LinkState`) |

### Frontend — Organización por feature

```
frontend/src/
├── app/              # Shell: Router, Layout, providers (Copilot, i18n, tour, etc.)
├── chat/             # UI de chat y estado: ChatUI, FloatingChat, cards, widgets
├── graph/            # Visualización del grafo (Sigma.js)
├── pages/            # Páginas por ruta (30+ archivos), lazy-loaded salvo Landing/Login
├── shared/           # Utilidades, API clients, auth store (Zustand), hooks
├── styles/           # Design tokens CSS + Tailwind overrides (~795 líneas)
├── ui/               # Primitivas UI propias (Button, Card, Input, etc.) — sin shadcn/ui ni MUI
├── widgets/          # Widgets a nivel de página (CookieConsent, NotificationCenter, etc.)
└── __tests__/        # Tests unitarios
```

---

## 4. Comandos de build, test y lint

### Backend (dentro del contenedor `backend` o con `uv` local)

```bash
# Dependencias
uv sync --all-extras

# Tests
uv run pytest -q
uv run pytest -q --cov=src --cov-report=xml --cov-report=term --cov-fail-under=40

# Lint
uv run ruff check src tests

# Type-check (permissivo en MVP; `continue-on-error: true` en CI)
uv run mypy src

# Migraciones
uv run alembic upgrade head
uv run alembic revision --autogenerate -m "descripción"

# Arrancar en dev
uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload

# Worker arq
arq src.shared.worker.WorkerSettings

# Seed manual de ESCO (la imagen Docker ya lo hace en startup)
python scripts/seed_esco.py

# Reset completo de ESCO (trunca + re-seed)
./scripts/reset-esco.sh
```

### Frontend (dentro del contenedor `frontend` o con `npm` local)

```bash
# Dependencias
npm install --include=dev

# Dev server
npm run dev          # Vite en 0.0.0.0:5173

# Build de producción
npm run build        # tsc -b && vite build

# Tests
npm test -- --run    # Vitest con jsdom

# Lint
npm run lint         # ESLint . --ext .ts,.tsx

# Type-check
npm run typecheck    # tsc --noEmit
```

### Stack completo (Docker Compose)

```bash
# Arrancar todo (requiere Docker Desktop, 8 GB RAM, puertos 5173/8000/8025/5432/6379 libres)
docker compose up -d --build
docker compose exec backend alembic upgrade head

# URLs locales
# Frontend: http://localhost:5173
# Backend/OpenAPI: http://localhost:8000/docs
# MailHog UI: http://localhost:8025
# Métricas Prometheus: http://localhost:8000/metrics

# Reset completo (destruye datos)
docker compose down -v && docker compose up -d --build
```

---

## 5. Guías de estilo

### Python
- **Formateo:** Ruff (quote-style `double`, indent-style `space`, line-length 100).
- **Lint rules activas:** E, F, W, I, N, UP, B, C4, SIM, RUF, ASYNC, PL, PIE, RET, TID.
- **Ignoradas intencionalmente:**
  - `PLR0913` (demasiados argumentos) — común en casos de uso DDD.
  - `PLR2004` (magic values) — validaciones de dominio suelen usar literales.
  - `E501` (línea larga) — gestionado por el formateador.
- **Tests:** se relajan `PLR2004`, `S101`, `ARG`, `N806`.
- **Alembic:** se relajan `E501`, `I001`.
- **Type-checking:** mypy en modo `strict` con plugin de Pydantic. Algunas librerías de terceros se ignoran (`weasyprint`, `docx`, `pgvector`, `arq`, `authlib`, `jose`, `mcp`).

### TypeScript / React
- **ESLint:** configuración flat en `frontend/eslint.config.js`.
- **Reglas clave:**
  - `react/react-in-jsx-scope: off` (React 19 con nuevo transform JSX).
  - `react/prop-types: off` (usamos TypeScript).
  - `@typescript-eslint/no-explicit-any: off` (MVP pragmático).
  - `@typescript-eslint/no-unused-vars: warn` con patrón `^_` para ignorar.
  - `react-hooks/rules-of-hooks: error`.
  - `react-hooks/exhaustive-deps: warn`.
- **TypeScript:** target ES2022, módulo ESNext, JSX `react-jsx`, `strict`, `noUnusedLocals`, `noUnusedParameters`, `isolatedModules`.

### Diseño / CSS
- Sistema de diseño propio basado en **Pirsch Analytics** (documentado en `DESIGN.md`).
- Tokens CSS en `frontend/src/styles/index.css` son la única fuente de verdad.
- Tailwind config mapea utilidades semánticas a esas variables.
- Colores principales: `midnight-ink` (#000000), `ghostly-gray` (#f8f5ed), `muted-stone` (#707070), `sunbeam-yellow` (#ffda6e), `leafy-green` (#6ece9d).
- No usar Google Fonts; las fuentes se auto-alojan vía `@fontsource`.
- Dark mode gestionado con `data-theme="dark"` en `<html>`.

---

## 6. Estrategia de testing

### Backend
- **Framework:** pytest 8+ con `pytest-asyncio` (modo auto), `pytest-cov`, `pytest-mock`.
- **Marcadores obligatorios:**
  - `unit` — lógica pura de dominio/aplicación, sin IO.
  - `integration` — toca base de datos o Redis.
  - `e2e` — flujo completo de API o MCP.
  - `slow` — tarda >1s.
- **Cobertura:** fuente `src/`, omite `src/main.py` y `alembic/*`. Umbral mínimo **40 %** (intencionalmente permisivo para el primer push; se apretará sprint a sprint).
- **Tests de migración:** matriz en `backend/tests/migrations/` validada en CI.

### Frontend
- **Framework:** Vitest 2.1 con entorno `jsdom`.
- **Testing Library:** `@testing-library/react` para componentes.
- **Tests:** pocos en MVP; el foco está en lint + typecheck + build en CI.

### CI/CD (`.github/workflows/ci.yml`)
Se ejecuta en push a `main` y en pull requests.

| Job | Qué hace |
|-----|----------|
| `backend` | Checkout → deps de sistema (WeasyPrint) → instala `uv` → `uv sync --all-extras` → crea extensiones pgvector/citext/pgcrypto → Alembic migrate → Ruff → Mypy (`continue-on-error`) → pytest con cobertura ≥40% → sube artifact `coverage.xml` (14 días) |
| `frontend` | Checkout → Node 22 + npm cache → `npm install --include=dev` → lint → typecheck → test (`--run`) → build |
| `security` | Trivy filesystem scan (CRITICAL/HIGH, `exit-code: 1`, `continue-on-error` por ahora) |

**Servicios del job backend:** `pgvector/pgvector:pg16` + `redis:7-alpine`.

---

## 7. Arquitectura de runtime y despliegue

### Local (Docker Compose dev)
Levanta 6 contenedores:

| Contenedor | Servicio | Puerto host | Notas |
|-----------|----------|-------------|-------|
| `cvs-postgres` | Postgres 16 + pgvector + AGE | 5432 | Datos en volumen `postgres_data` |
| `cvs-redis` | Redis 7 | 6379 | Cola arq + rate-limit |
| `cvs-mailhog` | SMTP de test | 1025 / 8025 | Captura todos los emails en dev |
| `cvs-backend` | FastAPI + Agno | 8000 | Hot-reload en `backend/src/` |
| `cvs-worker` | Worker arq | — | 12+ tareas registradas |
| `cvs-frontend` | Vite dev server | 5173 | Hot-reload en `frontend/src/` |

### Producción

**Opción A: Fly.io (recomendada)**
- Tres apps Fly: `cvs-saas-backend`, `cvs-saas-worker`, `cvs-saas-frontend`.
- Servicios gestionados: Fly Postgres (con pgvector), Upstash Redis.
- Volúmenes para claves JWT + fotos de perfil.
- Despliegue: `flyctl deploy --config fly.toml --remote-only` (ver `docs/OPERATIONS/DEPLOYMENT.md`).
- Migraciones: se ejecutan manualmente post-deploy vía SSH.

**Opción B: VPS Docker**
```bash
cp .env.example .env.production
# editar con valores reales
docker compose -f docker-compose.prod.yml --env-file .env.production up -d
docker compose -f docker-compose.prod.yml exec backend alembic upgrade head
```
Requiere nginx/Caddy delante para TLS.

### Health checks
- `GET /healthz` — liveness (siempre 200 si el proceso responde).
- `GET /readyz` — readiness (chequea DB, Redis, claves JWT, config LLM).
- `GET /metrics` — métricas Prometheus.

---

## 8. Configuración y variables de entorno

Copiar `.env.example` a `.env` en la raíz del repo. Docker Compose lo lee automáticamente.

**Valores por defecto funcionan offline** (todo mockeado). No se necesita ninguna credencial externa para arrancar el MVP.

| Servicio | Mock por defecto | Real (variable env) |
|----------|------------------|---------------------|
| LLM | `MockLlmClient` | `AGENTS_PROVIDER=anthropic\|openai` + API key |
| Embeddings | `sha256(text) → 1536 floats` | `EMBEDDINGS_PROVIDER=openai\|mistral` |
| Email | MailHog local | `EMAIL_PROVIDER=brevo\|postmark` |
| Almacenamiento | Filesystem (`./backend/var/documents/`) | `STORAGE_PROVIDER=s3` |
| Stripe | `MockStripeClient` | `STRIPE_PROVIDER=real` + keys |
| PDF parse | `MockPdfParser` | `AFFINDA_API_KEY` |
| Scraping | `MockJobScraper` | `SCRAPING_ENABLED=true` |
| ESCO seed | Automático en Docker | `AUTO_SEED_ESCO=true` |

**Variables de ESCO:**
- `AUTO_SEED_ESCO` — semilla automática al arrancar el contenedor (`true` en dev).
- `ESCO_VERSION` — tag de release guardado en `graph_ingest_meta` (ej. `v1.1.1`).
- `ESCO_DOWNLOAD_URL` — URL alternativa del ZIP de ESCO si la oficial no responde.

**Rate limiting de MCP:**
- `MCP_RATE_LIMIT_PER_MINUTE` / `MCP_RATE_LIMIT_PER_HOUR` / `MCP_RATE_LIMIT_PER_DAY` — límites específicos para el servidor MCP.

**Variables críticas en producción:**
- `DATABASE_URL`, `DATABASE_URL_SYNC`
- `REDIS_URL`
- `CANONICAL_BASE_URL`, `FRONTEND_BASE_URL`
- `CORS_ORIGINS` (sin localhost)
- `TOKEN_ENCRYPTION_KEY` (Fernet, generar nueva)
- `EMAIL_PROVIDER`, `EMAIL_FROM`
- `JWT_PRIVATE_KEY_PATH`, `JWT_PUBLIC_KEY_PATH` (RSA 2048, auto-generadas en primer arranque; montar volumen persistente)

El backend valida en startup (`validate_production_ready()`) que no haya valores de desarrollo en producción (contraseñas por defecto, URLs localhost, email mock, etc.).

---

## 9. Consideraciones de seguridad

- **Auth:** JWT RS256 con TTL de acceso 15 min y refresh 30 días. Claves RSA generadas automáticamente en primer arranque; deben persistir en volumen.
- **Contraseñas:** hasheadas con Argon2.
- **2FA:** soportada vía TOTP (pyOTP).
- **OAuth 2.1 AS propio:** implementa RFC 8414 (metadata), 9728 (DPoP), 8707 (PKCE), 7591 (DCR). Consent automático en dev; explícito en prod.
- **Rate limiting:** slowapi + limits con backend Redis. Límites específicos para MCP (`MCP_RATE_LIMIT_PER_MINUTE/HOUR/DAY`).
- **CORS:** restringido explícitamente; en prod nunca debe incluir localhost.
- **RLS:** PostgreSQL Row-Level Security por `user_id` (`app.current_user_id`) en todas las tablas de usuario.
- **Emails de verificación:** obligatorios en producción (`AUTO_VERIFY_EMAILS_IN_DEV=false` en prod).
- **Escaneo de seguridad:** Trivy en CI (actualmente `continue-on-error`, se endurecerá).
- **Secretos:** rotación documentada en `docs/OPERATIONS/SECRETS_ROTATION.md`.

---

## 10. Convenciones y patrones del proyecto

### Backend
- **Patrón Repository + Unit of Work:** cada contexto define puertos en `application/` e implementaciones en `infrastructure/`.
- **Event-driven:** bus de eventos in-process (`src/shared/events.py`). Los suscriptores se cablean en `main.py`.
- **Motor de Coherencia:** toda escritura en el universo pasa por `POST /api/v1/coherence/upsert`. Nunca se hace append ciego: se busca entidad existente (exacta → similitud semántica), se fusiona según reglas declarativas, se registra changelog (`universe_change_log`).
- **Auto-enrichment:** después de cada turno de chat, `UniverseEnrichmentEngine` extrae entidades y relaciones implícitas del mensaje del usuario y las materializa en el grafo AGE automáticamente (fire-and-forget). El grafo crece orgánicamente sin que el usuario tenga que usar comandos explícitos.
- **Descubrimiento conversacional (context → capture → enrich):** el intent `discover_profile` nunca usa exámenes. El flujo es:
  1. **Contexto:** `get_profile_completeness` revela qué dimensiones faltan.
  2. **Captura:** `suggest_discovery_questions` genera 1-3 preguntas naturales conectadas a lo que el usuario ya tiene ("Veo que…").
  3. **Enriquecimiento:** la respuesta fluye por `UniverseEnrichmentEngine` y se materializa en el grafo AGE + ESCO linking automático.
- **HITL proposal system:** toda escritura pasa por `propose_*` (Agno `external_execution=True`). El frontend renderiza una card (`EntryCard`, `QuestionnaireCard`, etc.); el usuario confirma, rechaza o edita. Solo entonces se emite `POST /api/v1/coherence/upsert`. Los rechazos alimentan el self-learning loop.
- **ESCO linking pipeline:** cada skill/entidad nueva se enlaza a ESCO en tres fases:
  1. **Embed:** pgvector top-K cosine sobre `ontology_embeddings`.
  2. **Rerank:** `FeatureReranker` (Jaro-Winkler 0.35 + Jaccard 0.25 + exact-bonus 0.20 + rank-decay 0.20) re-scorea candidatos.
  3. **Threshold:** ≥0.86 → auto-link (`LINKED`); ≥0.70 → quarantine (`SUGGESTED`, HITL); <0.70 → fallback a ontología custom (`ORPHAN`).
- **Self-learning feedback loop:** cuando un usuario rechaza o edita una propuesta, `record_agent_feedback` (vía `learning_tools.py`) guarda el evento en `user_procedural_memory`. Un workflow periódico (`consolidate`) agrega ejemplos similares en reglas activas que los `Context Providers` inyectan en las instrucciones del agente. Sin fine-tuning, solo *context engineering*.
- **Discovery progress REST + SSE:**
  - `GET /api/v1/discovery/progress` — score 0-100, coverage por dimensión, descubrimientos recientes, estadísticas ESCO.
  - `GET /api/v1/discovery/stream` — SSE que emite un evento JSON cada vez que se inserta una fila en `universe_change_log` para el usuario autenticado (heartbeat cada 15 s).
- **Single chat por usuario:** `thread_id = main-<user_id>`, con ventana deslizante de 40 mensajes + digest que pliega mensajes antiguos.
- **Mock-first:** toda integración externa tiene implementación mock que se activa por defecto. Cambiar el `*_PROVIDER` correspondiente y añadir la API key para usar la real.

### Frontend
- **Custom hash router:** usa `window.location.hash` para navegación, permitiendo hosting estático sin SSR.
- **Lazy loading:** solo `LandingPage` y `LoginPage` se cargan eagerly; el resto son `React.lazy()`.
- **Primitivas UI propias:** no usar shadcn/ui, MUI ni Bootstrap. Las primitivas están en `src/ui/`.
- **Colores semánticos en Tailwind:** `ink`, `stone`, `canvas`, `surface`, `hairline`, `sunbeam`, `leaf`, `brand`.
- **CopilotKit overrides:** estilos extensos en `src/styles/index.css` para integrar el chat con el diseño editorial de la app.

---

## 11. Documentación adicional

| Ruta | Contenido |
|------|-----------|
| `README.md` | Quickstart, arquitectura de alto nivel, golden paths |
| `DESIGN.md` | Referencia de estilo Pirsch (tokens, tipografía, componentes) |
| `docs/PLAN.md` | Especificación técnica completa + análisis de mercado |
| `docs/LOCAL_DEPLOY.md` | Guía detallada de despliegue local y troubleshooting |
| `docs/agents/` | Arquitectura de agentes, catálogo de tools, motor de coherencia, chat único |
| `docs/architecture/` | Flujo de agentes, Graph-RAG, capas de memoria, migración Agno |
| `docs/OPERATIONS/` | Despliegue, monitorización, backups, migraciones, rotación de secretos, costes, runbooks de incidencias |

---

## 12. Notas para el agente

- **Idioma principal de documentación:** español. El código usa inglés para nombres de variables/funciones/clases, pero comentarios, docs y mensajes de commit pueden estar en español.
- **No modificar `pyproject.toml` ni `package.json` sin justificación:** los rangos de versión están pinneados con cuidado (especialmente Agno, FastAPI, Pydantic v2).
- **Alembic antes de código nuevo con modelos:** si añades/quitas tablas o columnas, genera una migración con `alembic revision --autogenerate` y revísala antes de aplicar.
- **No romper import-linter:** si creas un nuevo contexto acotado, añade su contenedor a `backend/.importlinter` bajo la cláusula `layered`.
- **Tests en CI:** el umbral de cobertura es 40 %. Si reduces cobertura por debajo, el job de backend fallará.
- **Mypy es estricto pero permite fallo en CI:** no bloquea el merge actualmente (`continue-on-error: true`), pero se pretende endurecer.

---

## 13. Decisiones arquitectónicas post-auditoría (Sprint 0)

> Esta sección documenta cambios estructurales aprobados tras la auditoría integral de mayo 2026.

### 13.1 Frontend — Hooks compartidos
- **`useClickOutside(ref, onClose, enabled)`** y **`useEscapeKey(onClose, enabled)`** en `frontend/src/shared/`. Reemplazan 8+ implementaciones duplicadas de `useEffect` + `addEventListener("mousedown")` + `addEventListener("keydown")`.
- **Query keys centralizadas** en `frontend/src/shared/queryKeys.ts`. Elimina string literals dispersos (`["universe"]`, `["jobs"]`, etc.) y hace los invalidates type-safe.
- **`_activeChatSessionId`** movido de variable global de módulo a campo en `useChatState` (Zustand). Elimina estado mutable fuera de React.

### 13.2 Frontend — Primitivas UI nuevas
- **`Dialog`** — Modal accesible con `AnimatePresence`, backdrop blur, spring animation, Escape key handling.
- **`Tabs`** — Morphing-pill tabs con `layoutId` indicator de Motion.
- **`Tooltip`** — Tooltip simple con delay configurable.
- **`ShimmerSkeleton`** — Reemplaza `animate-pulse` por sweep animation horizontal.
- **`Button`** — Variantes `primary` y `secondary` ahora emiten `box-shadow` glow en hover (`glow-sunbeam`, `glow-leaf`).

### 13.3 Frontend — Diseño v2
- **Acento IA (`nova`)** — Color `#00d4aa` (cian) para identificar elementos impulsados por agentes.
- **Glow tokens** — `--glow-leaf`, `--glow-sunbeam`, `--glow-nova` en CSS vars.
- **Skeleton shimmer animation** — `@keyframes shimmer` con gradient sweep.
- **Profundidad de capas en dark mode** — `surface-canvas` → `surface-base` → `surface-raised` → `surface-overlay` (Linear-style).

### 13.4 Backend — Clean Architecture
- **`with_user_session(user_id)`** — Context manager en `shared/db.py` que reemplaza el boilerplate `get_session_factory() + set_rls_user()` repetido en ~20 archivos. Garantiza commit/rollback consistente.
- **Import-linter en CI** — Añadido job `uv run lint-imports` en `.github/workflows/ci.yml`.
- **`.importlinter` completo** — Todos los bounded contexts (`coherence`, `graph`, `agents`, `knowledge`, `notes`, `rubrics`, `integrations`) añadidos a la lista de containers.

### 13.5 CI/CD — Hardening
- **Branch trigger corregido** — `main` → `master` (el repo usa `master`).
- **`continue-on-error: true` eliminado** de mypy y Trivy. Los errores de tipo y vulnerabilidades CRITICAL/HIGH ahora bloquean el pipeline.
- **Dependencias muertas eliminadas** — `@tanstack/react-router`, `react-helmet-async`, `focus-trap-react`.
- **Dead code eliminado** — `RemindersBell.tsx` (funcionalidad absorbida por `NotificationCenter`).

### 13.6 Backend — Agno-first + Conversational Discovery (Sprint R)
- **Enfoque Universo Profesional único** — Career, jobs y social depriorizados. El universo actual = CV knowledge. Futuros "universos entrelazados" quedan para más adelante.
- **`quiz_skills` eliminado** — No se hacen exámenes ni quizzes. Reemplazado por `discover_profile`: el agente hace preguntas naturales sobre experiencias, proyectos y skills.
- **`UniverseEnrichmentEngine`** — Pipeline post-turno que extrae entidades/relaciones del texto libre del usuario y las materializa en AGE automáticamente (ER v2 + coherence). El grafo crece sin comandos explícitos.
- **Intent Router v2** — Fast-path keywords + LLM fallback. Intents activos: `expand_universe`, `generate_document`, `discover_profile`, `explore_graph`, `general_chat`. Career/Social providers existen en código pero están "apartados".
- **Discovery tools** — `get_profile_completeness` y `suggest_discovery_questions` permiten al agente hacer preguntas contextualizadas basadas en los huecos reales del perfil.
- **Graph auto-enrichment** — `enrich_user_graph` se ejecuta tras cada upsert para inferir edges adicionales (e.g., tech_stack → USES_TECH).
- **ESCO anchor** — Todos los skills se enlazan a ESCO donde sea posible. Cross-type dedup vía `esco_uri`.
- **Self-learning context** — 4-tier memory (semantic + procedural + episodic + working) con `SelfLearningEngine`. El modelo subyacente no cambia; el contexto alrededor evoluciona.
- **Discovery progress endpoint + SSE** — `GET /api/v1/discovery/progress` devuelve score 0-100; `GET /api/v1/discovery/stream` notifica en tiempo real vía Server-Sent Events.
- **Document specialist** — Especialista dedicado a generación de documentos con descubrimiento conversacional previo (kind → template → tone → language → JD opcional).
