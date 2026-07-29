# Production Readiness Checklist — Universo Profesional v1.0

| # | Área | Ítem | Estado | Notas |
|---|------|------|--------|-------|
| 1 | **Tests backend** | Integration: auth flow completo (register → verify → login → refresh) | ✅ | `tests/integration/test_auth_integration.py` |
| 2 | **Tests backend** | Integration: Universe CRUD con RLS | ✅ | `tests/integration/test_universe_rls.py` |
| 3 | **Tests backend** | Integration: Document generation con mock LLM | ✅ | `tests/integration/test_documents_integration.py` |
| 4 | **Tests backend** | Integration: Billing webhook con mock Stripe | ✅ | `tests/integration/test_billing_webhook.py` |
| 5 | **Tests backend** | Unit: identity password policy + JWT encode/decode | ✅ | `tests/unit/identity/` |
| 6 | **Tests backend** | Unit: billing quota enforcement + plan upgrades | ✅ | `tests/unit/billing/` |
| 7 | **Tests backend** | Unit: documents template rendering (PDF/DOCX) | — | Eliminado en la poda de la suite (918 → 165). El render se cubre end-to-end en `tests/integration/test_documents_integration.py` |
| 8 | **Tests backend** | 165 tests, puerta dura | ✅ | Suite curada (918 → 165). `ci.yml` la ejecuta como pass/fail, sin presupuesto de fallos. Sube `coverage.xml` como artefacto, pero no impone `--cov-fail-under` |
| 9 | **Tests frontend** | Componentes críticos: LoginPage, RegisterPage | ✅ | `frontend/src/__tests__/LoginPage.test.tsx` |
| 10 | **Tests frontend** | Wizard de onboarding | — | Obsoleto: el wizard se eliminó en favor de un onboarding chat-native (`frontend/src/pages/OnboardingChatPage.tsx`). No existe test unitario que lo cubra |
| 11 | **Tests frontend** | Chat/AG-UI wrapper (mock CopilotKit provider) | ✅ | `frontend/src/__tests__/CopilotProvider.test.tsx` |
| 12 | **Tests frontend** | MSW para interceptar llamadas API | ✅ | `frontend/src/__tests__/mocks/handlers.ts` + setup |
| 13 | **Seguridad** | Bandit ("S") en Ruff select | ✅ | `backend/pyproject.toml` |
| 14 | **Seguridad** | Trivy scan de imagen Docker en CI | ✅ | `.github/workflows/ci.yml` (build + scan) |
| 15 | **Seguridad** | `localhost` en `CORS_ORIGINS` rechaza arranque en prod | ✅ | `validate_production_ready()` + tests |
| 16 | **Observabilidad** | Exporter OTLP configurado | ✅ | `opentelemetry-exporter-otlp` + `src/shared/otel_setup.py` |
| 17 | **Observabilidad** | Métrica `cvs_user_registered_total` | ✅ | `src/shared/metrics.py` + hook en registro |
| 18 | **Observabilidad** | Métrica `cvs_cv_generated_total` | ✅ | `src/shared/metrics.py` + hook en `/documents/generate-cv` |
| 19 | **Observabilidad** | Métrica `cvs_mcp_invocations_total` | ✅ | Ya existía en `src/shared/metrics.py` |
| 20 | **Observabilidad** | Métrica `cvs_stripe_conversion_total` | ✅ | `src/shared/metrics.py` + hook en webhook Stripe |
| 21 | **Performance** | Load testing: 200 usuarios login + fetch universe (k6) | ✅ | `scripts/load/k6-auth-universe.js` |
| 22 | **Performance** | Load testing: 50 usuarios generando CV con LLM mock (k6) | ✅ | `scripts/load/k6-generate-cv.js` |
| 23 | **Performance** | Load testing: Locustfile con escenarios mixtos | ✅ | `backend/tests/load/locustfile.py` |
| 24 | **Performance** | Uvicorn workers configurados (gunicorn + uvicorn) | ✅ | `docker/backend.Dockerfile` + `WEB_CONCURRENCY` en compose |
| 25 | **Documentación** | Checklist de lanzamiento v1 | ✅ | `docs/OPERATIONS/LAUNCH_CHECKLIST_V1.md` |
| 26 | **Documentación** | Runbook de rollback | ✅ | `docs/OPERATIONS/ROLLBACK_RUNBOOK.md` |

## Archivos modificados / creados

### Backend
- `backend/pyproject.toml` — dependencias (`opentelemetry-exporter-otlp`, `gunicorn`, `locust`), ruff rules (+S), pytest markers
- `backend/src/shared/metrics.py` — métricas de negocio custom
- `backend/src/shared/otel_setup.py` — configuración OTLP exporter (nuevo)
- `backend/src/identity/application/use_cases.py` — hook `user_registered_total.inc()`
- `backend/src/documents/interfaces/api/router.py` — hook `cv_generated_total.inc()`
- `backend/src/billing/interfaces/api/router.py` — hook `stripe_conversion_total.inc()`
- `backend/tests/conftest.py` — `RATE_LIMIT_ENABLED=false` para tests, host `localhost`
- `backend/tests/integration/test_auth_integration.py` (nuevo)
- `backend/tests/integration/test_universe_rls.py` (nuevo)
- `backend/tests/integration/test_documents_integration.py` (nuevo)
- `backend/tests/integration/test_billing_webhook.py` (nuevo)
- `backend/tests/unit/identity/test_password_policy.py` (nuevo)
- `backend/tests/unit/identity/test_jwt.py` (nuevo)
- `backend/tests/unit/billing/test_quota.py` (nuevo)
- `backend/tests/unit/billing/test_plan_upgrades.py` (nuevo)
- `backend/tests/unit/test_config_production.py` (nuevo)
- `backend/tests/load/locustfile.py` (nuevo)

### Frontend
- `frontend/vite.config.ts` — `setupFiles: ["./src/__tests__/setup.ts"]`
- `frontend/src/__tests__/setup.ts` — MSW + IntersectionObserver mock
- `frontend/src/__tests__/mocks/server.ts` (nuevo)
- `frontend/src/__tests__/mocks/handlers.ts` (nuevo)
- `frontend/src/__tests__/test-utils.tsx` (nuevo)
- `frontend/src/__tests__/LoginPage.test.tsx` (nuevo)
- `frontend/src/__tests__/RegisterPage.test.tsx` (nuevo)
- `frontend/src/__tests__/CopilotProvider.test.tsx` (nuevo)

### Infra / CI
- `.github/workflows/ci.yml` — Trivy fs + image scan; sin umbral de coverage (ver ítem 8)
- `docker/backend.Dockerfile` — gunicorn + uvicorn workers
- `docker-compose.prod.yml` — `WEB_CONCURRENCY: ${WEB_CONCURRENCY:-2}`
- `.env.example` — `WEB_CONCURRENCY`, `OTLP_ENDPOINT`

### Documentación
- `docs/OPERATIONS/LAUNCH_CHECKLIST_V1.md` (nuevo)
- `docs/OPERATIONS/ROLLBACK_RUNBOOK.md` (nuevo)
- `docs/OPERATIONS/PRODUCTION_READINESS_CHECKLIST.md` (este archivo)

## Notas para CI

- Los tests de integración y e2e requieren Postgres + Redis. En GitHub Actions ya están configurados como services.
- Algunos tests asíncronos pueden fallar en **Windows local** por `RuntimeError: Event loop is closed` (limitación de `pytest-asyncio` + `ProactorEventLoop`). Esto **no afecta CI (Ubuntu)** ni producción.
- El coverage exacto en CI es la suma de unit + integration + e2e, pero no se
  impone ningún umbral: `coverage.xml` se publica como artefacto para consulta.
