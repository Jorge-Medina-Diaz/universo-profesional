# Universo Profesional — SaaS B2C (MVP)

Un SaaS B2C español que sustituye al "CV en Word" por un **Universo Profesional** versionado, con un servidor MCP remoto (OAuth 2.1 + PKCE + DCR) como diferenciador clave.

> **Estado:** MVP local (todo mockeado, sin credenciales externas). Ver [docs/PLAN.md](docs/PLAN.md) para la especificación técnica completa y de mercado.

---

## Quickstart

### Requisitos
- [Docker Desktop](https://www.docker.com/products/docker-desktop/) (Windows / macOS / Linux)
- 8 GB RAM disponibles
- Puertos libres: `5173` (frontend), `8000` (backend), `8025` (Mailhog UI), `5432` (postgres), `6379` (redis)

### Arrancar el stack

```powershell
# Windows PowerShell
docker compose up -d --build
docker compose exec backend alembic upgrade head
```

```bash
# bash / zsh
docker compose up -d --build
docker compose exec backend alembic upgrade head
```

### URLs locales
- **Frontend (Vite dev)**: <http://localhost:5173>
- **Backend (FastAPI)**: <http://localhost:8000>
- **OpenAPI docs**: <http://localhost:8000/docs>
- **Mailhog UI** (capturador de email): <http://localhost:8025>
- **Prometheus metrics**: <http://localhost:8000/metrics>
- **OAuth metadata**: <http://localhost:8000/.well-known/oauth-authorization-server>
- **MCP server-card**: <http://localhost:8000/.well-known/mcp/server-card.json>

### Tests

```powershell
docker compose exec backend pytest -q
docker compose exec frontend npm test -- --run
```

### Lint + type-check

```powershell
docker compose exec backend ruff check src tests
docker compose exec backend mypy src
docker compose exec frontend npm run lint
docker compose exec frontend npm run typecheck
```

---

## Arquitectura

```
[Web Browser (React 19 + Vite + Tailwind)] ⇣ [FastAPI app] ⇣ [Postgres + pgvector | Redis | filesystem | arq queue]
[MCP clients (Claude Code, Codex, Cursor, …)]  ⇣
```

- **Backend**: FastAPI 0.115 + SQLAlchemy 2.0 async + Pydantic v2, Clean Architecture por bounded context (DDD).
- **Frontend**: React 19 + Vite + TypeScript + Tailwind 4 + shadcn/ui + TanStack Query + TanStack Router + Zustand.
- **BBDD**: PostgreSQL 16 + pgvector 0.8 (HNSW index sobre embeddings 1536-d).
- **Queue**: Arq sobre Redis para tareas async (embeddings, renderizado PDF, scheduled hard-delete).
- **MCP**: SDK oficial Python `mcp` con Streamable HTTP transport + OAuth 2.1 AS local.

Ver [docs/PLAN.md](docs/PLAN.md) §G para diagramas y §H para el esquema de datos.

### Bounded contexts (`backend/src/`)
- `identity/` — registro, login, JWT, MFA, RGPD export/delete
- `universe/` — el "Universo Profesional" (educations, experiences, projects, skills, etc.) — **core del producto**
- `documents/` — CVs generados (inmutables, versionados, S3-emulado en filesystem)
- `ai_generation/` — pipeline RAG mockeado (parse JD → embed → retrieve top-K → rerank RRF → LLM mock → JSON Resume → WeasyPrint PDF + python-docx)
- `mcp_server/` — OAuth 2.1 AS (RFC 8414 + 9728 + 8707 + 7591) + 8 MCP tools
- `billing/` — quota enforcement + mock Stripe

---

## Servicios externos: todos mockeados

Este MVP **no requiere ninguna credencial externa**. Todas las integraciones tienen una implementación mock que se puede sustituir por la real cambiando un valor de env:

| Servicio | Mock | Real (env) |
|---|---|---|
| LLM | `MockLlmClient` (ensambla bullets reales del universo) | `LLM_PROVIDER=anthropic|openai|mistral` |
| Embeddings | `sha256(text) → 1536 floats normalizados` | `EMBEDDINGS_PROVIDER=openai|mistral` |
| Email | Mailhog SMTP local (UI en :8025) | `EMAIL_PROVIDER=postmark|brevo` |
| Storage | Filesystem local (`./backend/var/documents/`) | `STORAGE_PROVIDER=s3` |
| Stripe | `MockStripeClient` con endpoint `/billing/webhook/test` | `STRIPE_API_KEY=sk_test_…` |
| Affinda (PDF parse) | `MockPdfParser` canned response | `AFFINDA_API_KEY=…` |
| Scraping (JD) | `MockJobScraper` (devuelve JD pegada o fixture) | `SCRAPING_ENABLED=true` |

---

## Golden paths para validar

### 1. Web (browser)
1. `http://localhost:5173` → Register → email en Mailhog → click verify
2. Login → onboarding wizard → "empezar de cero" o importar LinkedIn ZIP (fixture en `frontend/fixtures/linkedin-export.zip`)
3. Universe editor → añadir educación + experiencia + skills
4. Generate CV → pegar JD de muestra → preview → descargar PDF/DOCX/JSON
5. Settings → Export RGPD → ZIP descargado
6. Settings → Delete account → soft delete (hard delete a 30 días)

### 2. MCP (terminal)
```powershell
docker compose exec backend python -m tests.e2e.mcp_oauth_flow
```
Este script simula un cliente MCP haciendo: DCR → authorize (consent automático) → token → llamadas a `get_universe_summary`, `add_education`, `match_job_to_profile`, `generate_cv`.

### 3. Conectar Claude Code (real)
```powershell
claude mcp add --transport http cvs-saas-local http://localhost:8000/mcp
```
El navegador se abrirá para completar el flow OAuth.

---

## Estructura del repo

```
CVs-SaaS/
├── docs/PLAN.md                   # Spec técnica + análisis de mercado
├── docker-compose.yml
├── docker/
│   ├── backend.Dockerfile
│   ├── worker.Dockerfile
│   └── frontend.Dockerfile
├── backend/                       # FastAPI + Clean Arch + DDD
│   ├── pyproject.toml
│   ├── alembic/
│   ├── src/
│   │   ├── shared/                # kernel: Result, Events, UoW, embeddings, db
│   │   ├── identity/
│   │   ├── universe/
│   │   ├── documents/
│   │   ├── ai_generation/
│   │   ├── billing/
│   │   ├── mcp_server/
│   │   └── main.py
│   ├── templates/                 # Jinja2 CV templates
│   └── tests/{unit,integration,e2e}
├── frontend/                      # React 19 + Vite
└── .github/workflows/ci.yml
```

---

## Lo que NO entra en el MVP

Cover letters, applications tracker, recordatorios, mobile app, más de 1 plantilla, multi-template, web push, Europass JSON-LD, BYOK, Stripe real, LLM real, Affinda real, email real, cloud deploy, plan Pro, PostHog/Sentry, DPO/EIPD. Ver §L del spec para roadmap completo a v1 y v2.

---

## Licencia

TBD — pendiente de decisión (probable: AGPLv3 para el core, con CLA para contribuciones).
