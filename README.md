# Universo Profesional — SaaS B2C (MVP)

Un SaaS B2C español que sustituye al "CV en Word" por un **Universo Profesional** versionado, con un servidor MCP remoto (OAuth 2.1 + PKCE + DCR) como diferenciador clave.

> **Estado:** MVP local (todo mockeado, sin credenciales externas). Ver [docs/PLAN.md](docs/PLAN.md) para la especificación técnica completa y de mercado.

---

## Quickstart — Levantar la app en terminal

### Requisitos
- [Docker Desktop](https://www.docker.com/products/docker-desktop/) (Windows / macOS / Linux)
- 8 GB RAM disponibles
- Puertos libres: `5173` (frontend), `8000` (backend), `8025` (Mailhog UI), `5432` (postgres), `6379` (redis)

### 1. Clonar y entrar al repo
```bash
git clone <repo-url>
cd CVs-SaaS
```

### 2. Configurar variables de entorno
```bash
# El repo incluye valores por defecto que funcionan offline (todo mockeado)
cp .env.example .env
```

### 3. Levantar el stack completo
```bash
# Construir imágenes y arrancar contenedores
docker compose up -d --build

# Aplicar migraciones de base de datos
docker compose exec backend alembic upgrade head

# Verificar que todo está saludable
docker compose ps
```

> **Primera vez o después de cambiar dependencias:** el `--build` es obligatorio. Para arrancar sin rebuild: `docker compose up -d`.

### 4. URLs locales
| Servicio | URL |
|----------|-----|
| Frontend (Vite dev) | <http://localhost:5173> |
| Backend (FastAPI) | <http://localhost:8000> |
| OpenAPI docs | <http://localhost:8000/docs> |
| MailHog UI (emails) | <http://localhost:8025> |
| Prometheus metrics | <http://localhost:8000/metrics> |
| Health check | <http://localhost:8000/healthz> |
| Readiness check | <http://localhost:8000/readyz> |

### 5. Crear un usuario de prueba
1. Abrir <http://localhost:5173>
2. Click en **"Crear cuenta"**
3. Rellenar nombre, email y contraseña (mín. 10 caracteres)
4. Ir a <http://localhost:8025> (MailHog) → abrir el email de verificación → click en el link
5. Login con el email y contraseña creados

> **Tip:** en desarrollo el consent OAuth y la verificación de email son automáticos si `AUTO_VERIFY_EMAILS_IN_DEV=true` (por defecto en `.env.example`).

### 6. Golden path para validar
1. **Onboarding:** después del login, completar el wizard de preferencias
2. **Universe:** añadir educación, experiencia y skills en <http://localhost:5173/#/universe>
3. **Generar CV:** ir a <http://localhost:5173/#/documents>, pegar una descripción de oferta de trabajo, generar y descargar PDF/DOCX
4. **Chat:** abrir el chat flotante y pedir "añade mi experiencia en Google como Senior Backend"
5. **MCP (terminal):**
   ```bash
   docker compose exec backend python -m tests.e2e.mcp_oauth_flow
   ```

### 7. Tests

```bash
# Backend (requiere deps de test en el contenedor)
docker compose exec backend bash -c 'pip install pytest pytest-asyncio pytest-cov pytest-mock httpx'
docker compose exec backend pytest -q

# Frontend
docker compose exec frontend npm test -- --run

# Con cobertura
docker compose exec backend pytest -q --cov=src --cov-report=term
```

### 8. Lint + type-check

```bash
# Backend
docker compose exec backend ruff check src tests
docker compose exec backend mypy src

# Frontend
docker compose exec frontend npm run lint
docker compose exec frontend npm run typecheck
```

### 9. Comandos útiles de desarrollo

```bash
# Ver logs en tiempo real
docker compose logs -f backend
docker compose logs -f frontend

# Reiniciar un servicio
docker compose restart backend

# Entrar al shell de un contenedor
docker compose exec backend bash
docker compose exec frontend sh

# Reconstruir solo el backend tras cambios en pyproject.toml
docker compose up -d --build backend worker

# Reset completo (borra DB, Redis y documentos)
docker compose down -v
docker compose up -d --build
docker compose exec backend alembic upgrade head
```

### Troubleshooting

| Síntoma | Solución |
|---------|----------|
| `port is already allocated` | Mata los procesos que usen los puertos: `docker compose down` o reinicia Docker Desktop |
| `alembic upgrade head` falla | Asegúrate de que `cvs-postgres` está healthy: `docker compose ps`. Si persistió, destruye el volumen: `docker compose down -v` |
| Frontend muestra blank page | Revisa que el backend responde: `curl http://localhost:8000/healthz`. Luego `docker compose restart frontend` |
| Emails no llegan a MailHog | Revisa `EMAIL_PROVIDER=mock` en `.env`. El contenedor `cvs-mailhog` debe estar `Up` |
| Tests de frontend fallan por Rollup | `docker compose exec frontend npm rebuild` o entra al contenedor y corre `npm test` desde ahí |
| `ModuleNotFoundError` en backend | El contenedor usa `uv sync` en build. Reconstruye: `docker compose up -d --build backend worker` |

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
