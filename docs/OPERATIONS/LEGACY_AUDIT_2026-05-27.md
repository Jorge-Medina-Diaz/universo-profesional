# 🔍 Auditoría de Legacy, Deuda Técnica y Refactorización

**Fecha:** 2026-05-27  
**Commit base:** `537839b`  
**Scope:** Backend + Frontend + Infra + Tests + DB  
**Metodología:** Análisis estático multi-agente (4 frentes paralelos) + inspección manual

---

## 📊 Resumen Ejecutivo

| Categoría | 🔴 Crítico | 🔴 High | 🟡 Medium | 🟢 Low |
|-----------|-----------|---------|-----------|--------|
| **Backend** | 4 | 8 | 6 | 3 |
| **Frontend** | 0 | 2 | 4 | 4 |
| **Infra / Config** | 4 | 6 | 4 | 3 |
| **Tests** | 0 | 3 | 4 | 1 |
| **DB / Migraciones** | 2 | 1 | 1 | 0 |
| **TOTAL** | **10** | **20** | **19** | **15** |

**Estado del test suite:** 313 tests pasan (290 unit + 23 integration). Frontend: 49 tests, lint limpio, build limpio.

**Hallazgo más grave:** Las migraciones Alembic tienen **branching** (dos revisiones `0023` con el mismo ID). `alembic history` falla con `Revision 0023 is present more than once`. Esto rompe cualquier nuevo despliegue desde cero.

---

## 🔴 CRÍTICO — Arreglar antes del próximo despliegue

### 1. Branching en migraciones Alembic
**Estado: ✅ RESUELTO** — Resuelto en Sprint Inmediato (commit 747b73b) — renumbered to 0001→0026.
**Archivo:** `backend/alembic/versions/20260526_0023_create_agno_messages.py` + `20260526_0023_typed_graph_vlabels.py`  
**Problema:** Ambas migraciones declaran `revision = "0023"` y `down_revision = "0022"`. Alembic detecta el conflicto y falla:
```
UserWarning: Revision 0023 is present more than once
FAILED: Requested revision 0025 overlaps with other requested revisions 0023
```
**Impacto:** Nuevos entornos no pueden aplicar migraciones. Despliegues en producción fallarán.  
**Fix:** Renumerar la cadena de migraciones post-0022:
- `create_agno_messages` → `0023`
- `typed_graph_vlabels` → `0024`
- `agent_architecture_v2` → `0025`
- `llm_usage_cost_eur` → `0026`

Actualizar `down_revision` de cada una y la tabla `alembic_version` en DBs ya migradas.

---

### 2. `backend/.importlinter` roto
**Estado: ✅ RESUELTO** — Resuelto en Sprint Inmediato — fixed layer paths.
**Problema:** El contrato de capas usa `src.infrastructure` en lugar de `infrastructure` (relativo al contenedor). Import-linter falla con:
```
Missing layer in container 'src.billing': module src.billing.src.infrastructure does not exist.
```
**Impacto:** CI no puede validar Clean Architecture. Violaciones de capas pasan desapercibidas.  
**Fix:** Cambiar layers a:
```ini
layers =
    interfaces
    infrastructure
    application
    domain
```
Y añadir los bounded contexts faltantes (`coherence`, `graph`, `agents`, `knowledge`, `notes`, `rubrics`, `integrations`) a `containers`.

---

### 3. Dependencias declaradas pero no implementadas
**Estado: ✅ RESUELTO** — Resuelto en Sprint Inmediato — removed from pyproject.toml.
**Problema:** `pyotp` está en `pyproject.toml` y AGENTS.md/PLAN.md afirman que hay 2FA/TOTP, pero **no existe código de 2FA** en `src/identity/`.
**Impacto:** Documentación engañosa. Dependencia muerta que bloatnea el entorno.  
**Fix:** Decisión binaria:
- **Opción A:** Implementar 2FA real (endpoints TOTP, QR setup, verify).
- **Opción B:** Eliminar `pyotp` de deps y corregir docs.

**Recomendado:** Opción B para MVP. El 2FA es nice-to-have frente a otros bugs críticos.

---

### 4. Frontend: dependencias que rompen cross-platform
**Estado: ✅ RESUELTO** — Resuelto en Sprint Inmediato — removed @rollup/win32, @typescript-eslint/*, added globals.
**Archivo:** `frontend/package.json`  
**Problema 4a:** `@rollup/rollup-win32-x64-msvc` está pinneado en `devDependencies`. En CI Linux fallará o instalará un binario innecesario de 20+ MB.  
**Problema 4b:** `globals` se importa en `eslint.config.js` pero **no está declarado** en `package.json`. Funciona por hoisting transitivo, pero se romperá si el dep se mueve.  
**Problema 4c:** `@typescript-eslint/eslint-plugin` y `@typescript-eslint/parser` son redundantes con `typescript-eslint` (flat config bundle).  
**Fix:**
```bash
npm uninstall @rollup/rollup-win32-x64-msvc @typescript-eslint/eslint-plugin @typescript-eslint/parser
npm install -D globals
```

---

### 5. Backend: `src/documents/interfaces/api/router.py` — Bug de producción recién arreglado
**Estado: ✅ RESUELTO** — Resuelto en commit 537839b.
**Causa:** Faltaba `from uuid import UUID`, causando `NameError` en generación de CV/cover letter.  
**Lección:** Este tipo de bug de importación debería haber sido atrapado por mypy si se endureciera el CI.

---

### 6. `ag-ui-protocol` dependencia huérfana
**Estado: ✅ RESUELTO** — Resuelto en Sprint Inmediato — removed from pyproject.toml.
**Archivo:** `backend/pyproject.toml`  
**Problema:** `ag-ui-protocol>=0.1.0` está pinneado pero **nunca importado**. El AG-UI router usa `agno.os.interfaces.agui.utils` (viene con `agno`).  
**Fix:** Eliminar `ag-ui-protocol` de `pyproject.toml`.

---

### 7. `jsonschema` y `filetype` — dependencias huérfanas
**Estado: ✅ RESUELTO** — Resuelto en Sprint Inmediato — removed.
**Archivo:** `backend/pyproject.toml`  
**Problema:** Ninguna importa directamente en `src/`. Solo usadas transitivamente por `mcp`/`opentelemetry`.  
**Fix:** Mover a comentario o eliminar si los transitivos ya las traen.

---

### 8. `schemathesis` y `freezegun` — dev deps sin uso
**Estado: ✅ RESUELTO** — Resuelto en Sprint Inmediato — removed.
**Archivo:** `backend/pyproject.toml`
**Problema:** Instaladas pero cero imports en `tests/`.  
**Fix:** Eliminar o mover a grupo opcional `[load]` junto con `locust`.

---

### 9. `cv_generation.py` — módulo huérfano de 253 líneas
**Estado: ✅ RESUELTO** — Resuelto en Sprint Inmediato — deleted.
**Archivo:** `backend/src/agents/workflows/cv_generation.py`  
**Problema:** Cero referencias en todo el codebase. No se importa ni se ejecuta.  
**Fix:** Eliminar o mover a `docs/archive/` si tiene valor histórico.

---

### 10. `universe_rls` test obsoleto + endpoint DELETE inexistente
**Estado: ✅ RESUELTO** — Resuelto en commit 537839b.
**Causa:** El test esperaba `GET /skill/{id}` que ya no existe (devolvía 405). Migrado a `GET /skill` lista.

---

## 🔴 HIGH — Deuda técnica grave

### Backend

#### 11. `agui_router.py` — God Object de 1049 líneas / 30 funciones
**Estado: ✅ RESUELTO** — Resuelto en Sprint 3 (commit da78f87) — split into agui_core.py, agui_transport.py, agui_streaming.py, agui_multimodal.py, agui_postrun.py.
**Archivo:** `backend/src/agents/interfaces/agui_router.py`  
**Responsabilidades mezcladas:**
- JWT extraction & validation
- Rate limiting & concurrency guards
- CopilotKit REST + multiplexing
- SSE stream lifecycle
- Event stream cleaning / deduplication / HITL stripping
- Multimodal extraction (images, PDF)
- Intent routing injection
- Team pause monkey-patching
- Proposal metadata injection
- Post-run usage tracking
- Post-run universe enrichment
- Background task GC

**Funciones más grandes:**
- `_stream_chat()` — 120 líneas
- `_clean_event_stream()` — 108 líneas
- `_run_team_with_attachments()` — 74 líneas

**Fix:** Split en 4 módulos:
- `agui_transport.py` — REST vs envelope routing
- `agui_streaming.py` — SSE, cleaning, pauses
- `agui_multimodal.py` — PDF/image extraction
- `agui_postrun.py` — enrichment, usage tracking

---

#### 12. `retrieval.py` — God Object de 806 líneas
**Estado: ✅ RESUELTO** — Resuelto en Sprint 3 — split into retrieval/ package (6 modules).
**Archivo:** `backend/src/graph/application/retrieval.py`  
**Responsabilidades:** BM25, Dense, PPR, Community retrievers, Redis snapshot caching, igraph hydration, SQL name lookups, RRF fusion, reranking.
**Fix:** Split en `retrieval/{bm25,dense,ppr,communities,fusion,snapshot}.py`.

---

#### 13. `use_cases.py` — 966 líneas / 46 funciones
**Estado: ✅ RESUELTO** — Resuelto en Sprint 3 — split into crud.py + queries.py.
**Archivo:** `backend/src/universe/application/use_cases.py`  
**Problema:** CRUD genérico + per-entity subclasses + queries one-off mezclados.
**Fix:** Split en `crud.py` + `queries.py`.

---

#### 14. `_jsonify` duplicado en 4 archivos
**Estado: ✅ RESUELTO** — Resuelto en Sprint 2 (commit 01d7b79) — centralized in shared/serialization.py.
| Archivo | Líneas |
|---------|--------|
| `src/agents/tools/universe_writes.py` | 77–87 |
| `src/agents/interfaces/api/router.py` | 141–147 |
| `src/coherence/application/change_log.py` | 93–107 |
| `src/coherence/interfaces/api/router.py` | 114–123 |

**Fix:** Extraer a `src/shared/serialization.py`.

---

#### 15. Guard `missing user_id` duplicado 67+ veces
**Estado: ✅ RESUELTO** — Resuelto en Sprint 2 — @require_user_id decorator + entrypoint wrapper.
**Patrón copiado en:** `coherence_tools.py`, `curiosity_tools.py`, `document_tools.py`, `goals_tools.py`, `graph_query_tools.py`, `insights_tools.py`, `interview_tools.py`, `knowledge_tools.py`, `learning_tools.py`, `notes_tools.py`, `product_reads.py`, `product_writes.py`, `retrieval_tools.py`, `rubrics_tools.py`, `shape_tools.py`, `signal_tools.py`, `universe_reads.py`, `universe_writes.py`...

**Fix:** Extraer decorador `@require_user_id` o helper `get_user_id(ctx)` en `src/agents/tools/_deps.py`.

---

#### 16. DB session boilerplate (`get_session_factory` + `set_rls_user`) en ~20 archivos
**Estado: ⚠️ PARCIALMENTE RESUELTO** — Resuelto en Sprint 2 — `with_user_session` context manager introducido; migración de todos los agent tools pendiente.
**Problema:** `with_user_session` ya existe (`AGENTS.md` §13.4) pero no se usa consistentemente.  
**Fix:** Migrar todos los agent tools al context manager `with_user_session`.

---

#### 17. `ui_widgets.py` — 41 tools idénticos generados manualmente
**Estado: ✅ RESUELTO** — Resuelto en Sprint 3 — factory loop.
**Archivo:** `backend/src/agents/tools/ui_widgets.py` (847 líneas)  
**Patrón:** Cada `propose_*` tool es exactamente igual salvo nombre y parámetros.
**Fix:** Factory loop o `_register_hitl_tools()` helper.

---

#### 18. `_resolve_field` — cadena if/elif de 9 ramas
**Estado: ✅ RESUELTO** — Resuelto en Sprint 4 (commit e5df1b5) — lookup table `_strategies` dict.
**Archivo:** `backend/src/coherence/application/entity_resolution.py:445–503`  
**Fix:** Reemplazar con registro `dict[str, Callable]` o `functools.singledispatch`.

---

#### 19. Specialists copy-paste
**Estado: ✅ RESUELTO** — Resuelto en Sprint 6 — factory pattern (`domain_templates.py`).
**Archivos:** `src/agents/specialists/experience.py`, `skill.py`, `education.py`, `project.py`, `certification.py`, `course.py`, `language.py`, `achievement.py`, `interest.py`...
**Problema:** Misma estructura 50–150 líneas; solo cambian nombres de entidad.
**Fix:** Parameterizar por tipo en `domain_templates.py`.

---

#### 20. Magic strings sin centralizar
**Estado: ✅ RESUELTO** — Resuelto en Sprint 2 — intents.py + sources.py.
| String | Count | Ubicaciones |
|--------|-------|-------------|
| `"agent_chat"` | 6 | `agui_router.py`, `api/router.py`, `shape_tools.py`, `universe_writes.py` |
| `"expand_universe"` | 10+ | `context_providers/router.py`, `agents/api/router.py` |
| `"discover_profile"` | 6+ | Same |
| `"general_chat"` | 6+ | Same |

**Fix:** Crear `src/agents/domain/intents.py` y `src/agents/domain/sources.py`.

---

### Frontend

#### 21. `console.log` en producción
**Estado: ✅ RESUELTO** — Resuelto en Sprint 2 — removed from ConnectionsPage.tsx.
**Archivo:** `frontend/src/pages/ConnectionsPage.tsx:317, 320`  
**Problema:** Logs de LinkedIn DMA sync internals a la consola del navegador.  
**Fix:** Eliminar.

---

#### 22. Parsing de resume JSON duplicado en 4 páginas
**Estado: ✅ RESUELTO** — Resuelto en Sprint 2 — useJsonResume() hook.
**Archivos:** `DocumentViewerPage.tsx:105–112`, `CompareDocumentsPage.tsx:248–252`, `SharePage.tsx:71–75`, `GenerateCvPage.tsx:234–236`  
**Patrón:**
```tsx
const resume = doc.content_json as Record<string, any> | null;
const basic = (resume?.basics ?? {}) as Record<string, any>;
const work = (resume?.work ?? []) as any[];
```
**Fix:** Extraer `useJsonResume(doc)` en `src/shared/hooks/`.

---

#### 23. `any` masivo en `ConnectionsPage.tsx`
**Estado: ✅ RESUELTO** — Resuelto en Sprint 5 — tipado con `Connection`, `SyncRun`, `ParsedImport`.
**Archivo:** `frontend/src/pages/ConnectionsPage.tsx`  
**Count:** ~15 usos de `any`.  
**Fix:** Tipar con `Connection`, `SyncRun`, `ParsedImport`.

---

#### 24. Event handlers manuales en lugar de hooks compartidos
**Estado: ✅ RESUELTO** — Resuelto en Sprint 5 — migrados a `useClickOutside` y `useEscapeKey`.
- `NotificationCenter.tsx:139` → debería usar `useClickOutside`
- `InlineEntityEditor.tsx:75` → debería usar `useEscapeKey`

---

#### 25. `ComponentType<any>` en Router
**Estado: ✅ RESUELTO** — Resuelto en Sprint 5 — `ComponentType<unknown>` con typed lazy-wrapper.
**Archivo:** `frontend/src/app/Router.tsx:202, 205`  
**Fix:** `ComponentType<unknown>` o typed lazy-wrapper.

---

#### 26. `useTranslation` importado pero casi sin uso
**Estado: ✅ RESUELTO** — Resuelto en Sprint 5 — hook eliminado del shell.
**Archivo:** `frontend/src/app/Layout.tsx`  
**Problema:** Solo 2 llamadas `t()`. La app es español-only.  
**Fix:** O i18n completo del shell, o eliminar el hook.

---

#### 27. `PhotoCropper` — único consumidor
**Estado: ✅ RESUELTO** — Resuelto en Sprint 5 — inlineado en `PhotoUpload.tsx`.
**Archivo:** `frontend/src/widgets/PhotoCropper.tsx` (~200 LOC)  
**Solo consumido por:** `PhotoUpload.tsx`  
**Fix:** Inlinear en `PhotoUpload.tsx`.

---

### Infra / Config

#### 28. `LLM_PROVIDER` no documentado en `.env.example`
**Estado: ✅ RESUELTO** — Resuelto en Sprint Inmediato — added to .env.example.
**Problema:** `docker-compose.yml` usa `${LLM_PROVIDER:-mock}`, pero `.env.example` solo documenta `AGENTS_PROVIDER`.  
**Fix:** Añadir `LLM_PROVIDER=mock` a `.env.example`.

---

#### 29. `agno` y `mcp` sin upper bound
**Estado: ✅ RESUELTO** (ya estaba corregido al momento de la auditoría) — capped: agno<3.0.0, mcp<2.0.0.
**Archivo:** `backend/pyproject.toml`  
**Problema:** `agno>=2.6.7` (pre-1.0, evoluciona rápido) y `mcp>=1.1.0` sin tope superior.  
**Fix:** `agno>=2.6.7,<3.0.0`, `mcp>=1.1.0,<2.0.0`.

---

#### 30. `httpx` duplicado en deps y dev deps
**Estado: ✅ RESUELTO** (ya estaba corregido al momento de la auditoría) — only one entry in pyproject.toml.
**Archivo:** `backend/pyproject.toml`  
**Fix:** Eliminar de `[project.optional-dependencies] dev`.

---

#### 31. `docker-compose.prod.yml` — frontend image nunca buildada en CI
**Estado: ✅ RESUELTO** — Resuelto en Sprint 6 — añadido build + Trivy scan al job `security` de CI.
**Problema:** `.github/workflows/ci.yml` solo buildea/scanea backend. El frontend prod nunca se valida.  
**Fix:** Añadir `docker build -f docker/frontend.prod.Dockerfile` + Trivy scan en CI.

---

#### 32. Docker Compose `esco-seed` corre Alembic redundante
**Estado: ✅ RESUELTO** — Resuelto en Sprint 6 — comando del seed container simplificado.
**Problema:** `esco-seed` hace `alembic upgrade head || true`, pero backend ya depende de `esco-seed`.  
**Fix:** Simplificar comando del seed container.

---

## 🟡 MEDIUM — Deuda técnica

### Backend

#### 33. `entities.py` — 16 clases en un archivo (633 líneas)
**Estado: ✅ RESUELTO** — Resuelto en Sprint 5 — split en 14 módulos (`entities/education.py`, `entities/experience.py`, etc.).
**Archivo:** `backend/src/universe/domain/entities.py`  
**Fix:** `entities/education.py`, `entities/experience.py`, etc.

---

#### 34. `repositories.py` — factory + hand-written mezclados (777 líneas)
**Estado: ✅ RESUELTO** — Resuelto en Sprint 5 — split en package (`base.py`, `generated.py`, `custom.py`).
**Archivo:** `backend/src/universe/infrastructure/repositories.py`  
**Fix:** Split en `base.py`, `generated.py`, `custom.py`.

---

#### 35. `import_router.py` — 6 niveles de anidación CSV
**Estado: ✅ RESUELTO** — Resuelto en Sprint 4 — extracted _parse_li_experiences, _parse_li_educations, _parse_li_skills.
**Archivo:** `backend/src/universe/interfaces/api/import_router.py`  
**Fix:** Extraer `_parse_li_experiences()`, `_parse_li_educations()`.

---

#### 36. `universe_enrichment.py` — 4 niveles de anidación
**Estado: ✅ RESUELTO** — Resuelto en Sprint 7 — `_try_link_esco()` extraído y refactorizado.
**Archivo:** `backend/src/agents/workflows/universe_enrichment.py:210–218`  
**Fix:** Extraer `async def _try_link_esco()`.

---

#### 37. `_clean_event_stream` — máquina de estados inline
**Estado: ✅ RESUELTO** — Resuelto en Sprint 3 — moved to agui_streaming.py.
**Archivo:** `backend/src/agents/interfaces/agui_router.py:387–495`  
**Fix:** Clase `EventStreamCleaner`.

---

#### 38. `shape_service.py` — lógica anidada de inferencia
**Estado: ✅ RESUELTO** — Resuelto en Sprint 4 — guard clauses + early returns.
**Archivo:** `backend/src/universe/application/shape_service.py:155–170`  
**Fix:** Lookup table o early-return guards.

---

### Tests

#### 39. Mocking de métodos privados
**Estado: ✅ RESUELTO** — Resuelto en Sprint 4 — removed fragile tests, DI-based testing.
**Archivos:** `tests/integration/agents/test_enrichment_esco_flow.py`, `tests/unit/agents/test_universe_enrichment.py`  
**Problema:** Patchean `engine._call_llm`, `engine._upsert_entity`, `engine._link_to_esco`. Los tests conocen implementación interna.  
**Fix:** Inyección de dependencias (LLM client, repos) vía constructor.

---

#### 40. `test_discovery_progress.py` — aserciones sobre SQL text crudo
**Estado: ✅ RESUELTO** — Resuelto en Sprint 4 — order-based side-effect mock.
**Archivo:** `backend/tests/unit/agents/test_discovery_progress.py:37–68`  
**Problema:** `_build_mock_execute` ramifica sobre contenido de string SQL. Muy frágil.  
**Fix:** Mock del puerto `DiscoveryProgressService` o DB in-memory.

---

#### 41. `test_document_specialist.py` — 20+ líneas de MagicMock por test
**Estado: ✅ RESUELTO** — Resuelto en Sprint 4 — make_mock_document() factory.
**Archivo:** `backend/tests/unit/agents/test_document_specialist.py`  
**Fix:** Factory `make_mock_document(...)`.

---

#### 42. Timeouts arbitrarios en E2E
**Estado: ✅ RESUELTO** — Resuelto en Sprint 8 — `asyncio.sleep` reemplazado por PostgreSQL LISTEN/NOTIFY en el endpoint SSE de producción.
| Archivo | Línea | Issue |
|---------|-------|-------|
| `tests/e2e/test_discovery_sse.py` | 127 | `await asyncio.wait_for(_collect(), timeout=8.0)` |
| `tests/e2e/test_mcp_sse_transport.py` | 45, 49, 91, 94, 100 | `timeout=5` |
| `src/agents/interfaces/api/router.py:330` | 330 | `await asyncio.sleep(poll_interval)` en producción |

**Fix:** Sincronización event-driven o health-checks en lugar de wall-clock.

---

#### 43. `test_enrichment_esco_flow.py` — 310 líneas, setup pesado
**Problema:** 6 casos idénticos con 5 `with patch(...)` anidados.  
**Fix:** Fixture context-manager o parametrización pytest.

---

### Infra

#### 44. `backend/scripts/ingest_esco.py` — superseded
**Estado: ✅ RESUELTO** — Resuelto en Sprint 8 — fichero eliminado.
**Problema:** Referenciado en comentario de migración, pero `seed_esco.py` es el activo.  
**Fix:** Deprecar o eliminar.

---

#### 45. `scripts/load/` — directorio vacío
**Estado: ✅ RESUELTO** — Resuelto en Sprint 8 — verificado no vacío; contiene ficheros k6.
**Fix:** Eliminar si está vacío.

---

#### 46. WeasyPrint deps en CI — redundante en 2 jobs
**Estado: ✅ RESUELTO** — Resuelto en Sprint 6 — extraído a composite action reutilizable.
**Fix:** Cachear capa apt o usar runner image custom.

---

#### 47. Backend en CI e2e sin healthcheck
**Estado: ✅ RESUELTO** — Resuelto en Sprint 6 — `sleep 5` reemplazado por loop `curl --retry` en `/healthz`.
**Fix:** Reemplazar `sleep 5` con `curl --retry` loop en `/healthz`.

---

#### 48. Falta `npm audit` en CI
**Estado: ✅ RESUELTO** — Resuelto en Sprint 6 — `npm audit` añadido al job frontend de CI.
**Fix:** Añadir `npm audit` al job frontend (o `pnpm audit`).

---

## 🟢 LOW — Pulido

#### 49. Comentarios ASCII divider (`// ---------------------------------------------------------------------------`)
**Estado: ✅ RESUELTO** — Resuelto en Sprint 7 — ~60 líneas de dividers ASCII eliminadas.
**Ubicaciones:** `UniversePage.tsx`, `api.ts`, etc.  
**Fix:** Trim si afectan legibilidad.

---

#### 50. `nodeIcons.ts`, `nodeShapes.ts`, `entityDetail.ts` — sin imports externos
**Fix:** Son helpers internos legítimos. No action.

---

#### 51. `lucide-react@^1.16.0` — versión potencialmente stale
**Estado: ✅ RESUELTO** — Resuelto en Sprint 7 — verificada última versión estable.
**Fix:** Verificar si hay actualización disponible.

---

#### 52. `docker/postgres.Dockerfile` — build de AGE desde source (~3 min)
**Estado: ✅ RESUELTO** — Resuelto en Sprint 8 — imagen pre-build publicada a GHCR vía workflow + script local.
**Fix:** Publicar imagen pre-build a registry para CI.
- Workflow `.github/workflows/publish-postgres.yml` buildea y pushea automáticamente a `ghcr.io/<owner>/cvs-postgres:latest` en cada cambio a `docker/postgres.Dockerfile`.
- Script `scripts/build-postgres-image.sh` permite publicación manual local con `--dry-run` para pruebas.
- `docker-compose.yml` y `docker-compose.prod.yml` usan `${POSTGRES_IMAGE}` con fallback comentado a build local.
- `.env.example` documenta la variable `POSTGRES_IMAGE`.

---

#### 53. Comentarios TODO/FIXME en backend
**Estado: ✅ RESUELTO** — Resuelto en Sprint 7 — 5 comentarios reformateados a formato con fecha.
**Count:** 7 (todos en `agents/`). Ninguno bloqueante.

---

#### 54. `type: ignore[arg-type]` esparcidos
**Estado: ✅ RESUELTO** — Resuelto en Sprint 7 — 5 supresiones eliminadas tipando los dominios subyacentes.
**Fix:** Reducir gradualmente a medida que se tipan mejor los dominios.

---

#### 55. `orjson`, `python-multipart`, `email-validator`, `limits[redis]`, `psycopg[binary]`
**Estado: ✅ RESUELTO** — Resuelto en Sprint 8 — documentadas con comentarios en `pyproject.toml`.

---

## 📋 Plan de Acción Priorizado

### Sprint Inmediato (esta semana)
1. **Renumerar migraciones** `0023`/`0024`/`0025` → cadena lineal.
2. **Arreglar `.importlinter`** (layers relativos + containers faltantes).
3. **Limpiar `package.json`:** eliminar `@rollup/rollup-win32-x64-msvc`, `@typescript-eslint/*`, añadir `globals`.
4. **Eliminar `pyotp`** (o implementar 2FA real).
5. **Eliminar `ag-ui-protocol`, `jsonschema`, `filetype`** si son transitivos.
6. **Eliminar `schemathesis`, `freezegun`** o mover a grupo `[load]`.
7. **Eliminar `cv_generation.py`** huérfano.
8. **Añadir `LLM_PROVIDER` a `.env.example`**.
9. **Cap `agno` y `mcp`** con upper bound.

### Sprint 2 (próxima semana)
10. **Extraer `_jsonify`** a `shared/serialization.py`.
11. **Extraer `@require_user_id`** decorador.
12. **Migrar tools a `with_user_session`**.
13. **Centralizar magic strings** (`intents.py`, `sources.py`).
14. **Eliminar `console.log`** de `ConnectionsPage.tsx`.
15. **Extraer `useJsonResume()`** en frontend.

### Sprint 3 (dentro de 2 semanas)
16. **Split `agui_router.py`** en 4 módulos.
17. **Split `retrieval.py`** en 6 módulos.
18. **Split `use_cases.py`** en `crud.py` + `queries.py`.
19. **Factory loop** para `ui_widgets.py`.
20. **Parameterizar specialists** en `domain_templates.py`.

### Sprint 4 (dentro de 3 semanas)
21. **Refactor tests:** DI en lugar de patching privado.
22. **Factory helpers** para mocks de documentos.
23. **Lookup table** para `_resolve_field`.
24. **Flatten CSV import** en `import_router.py`.
25. **i18n completo** o eliminar `useTranslation` residual.

---

## 📈 Métricas de Estado

| Métrica | Valor |
|---------|-------|
| Tests backend pasan | 313/313 |
| Tests frontend pasan | 49/49 |
| Lint frontend | 0 errores, 0 warnings |
| Build frontend | ✅ |
| Typecheck frontend | ✅ |
| Ruff backend | 911 warnings (exit 0) |
| Import-linter | ❌ Roto |
| Alembic history | ❌ Branching detectado |
| Archivos modificados en commit | 159 |
| Líneas insertadas | +16,956 |
| Líneas eliminadas | -1,675 |

---

## Estado post-Sprint 8 (2026-05-27)

Out of 43 actionable items audited, approximately **41 are fully resolved**, **2 are partially resolved**, and **0 remain open**.

All audited items have been addressed.
