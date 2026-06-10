# Pendientes — Universo Profesional

> Última actualización: 2026-06-09
> Fuente de verdad para el trabajo en curso: el **plan de transformación**
> (6 fases: foundations → AgentOS+latencia → GenUI agent-native → loops
> proactivos del KB → diseño del twin público → ops de producción).
> Este archivo solo lista lo NO cubierto por ese plan o deuda conocida.

## ✅ Corrección de deuda documental (2026-06-09)

La versión anterior de este archivo afirmaba como "faltantes" cosas que
llevan semanas construidas: S3 (`shared/storage.py:S3StorageAdapter`),
MFA/TOTP nativo, recordatorios + cron de dispatch, BYOK con UI, exports
JSON Resume + Europass, application tracker tipado, match scoring
desglosado. Todo eso EXISTE. Lo único de aquella lista aún cierto:

| Tema | Estado real |
|------|-------------|
| **Mypy strict** | ~495 errores preexistentes; no bloquea pero dificulta refactors |
| **SEO/GEO landing** | Sin `llms.txt`, Schema.org ni meta optimizados (cubierto por fase Twin del plan) |
| **Multi-idioma** | i18n configurado; faltan traducciones EN/CA/GL en muchas páginas |
| **Alertas de cuota MCP** | Sin aviso al acercarse al límite de invocaciones |
| **S3 runtime** | Adaptador completo pero sin verificar contra un bucket real (fase 5 del plan) |

## 🔜 Siguiente pase del plan de transformación (P3 restante + P5)

- **P3.C** — rutear `github_sync` por el motor de coherencia (hoy escribe
  repos directos: sin ESCO/edges/embeddings) + deep-extract LLM por repo;
  card `propose_linkedin_csv_import` (promover `linkedin_csv_deep.py`).
- **P3.E** — endpoint agregado `review-queue` + sheet FE + badge Home;
  métrica `cvs_ingestion_to_queryable_seconds` (SLO p95 ≤ 60s).
- **P5** — verificación S3 runtime, `min_machines_running=2`, Playwright
  golden path nocturno, métricas de negocio (onboarding/captura/nudges).
- Pulir: chip de estado ante RUN_ERROR (gate isLoading), ruta `/goals`
  (añadir al Router o retirar), suggestions nativas de CopilotKit.

## 🔶 Deuda heredada del pase de auditoría (deferred-by-design)

- **R4 slices 2-4** — proyección snapshot/AGE por outbox + rebuild-from-SQL.
- **R10** — LinkedIn auto-resync (GitHub semanal ya existe) + Review-queue FE
  (la fase 3 del plan lo absorbe).
- **R15 slice 3** — dirty-flag por change_log para el enrichment.
- **T4** — colapso de tokens `--cos-*` + pulido visual de la landing.
- **T7** — `Page[T]` en universe/mcp-stats + `response_model` + regeneración
  del cliente TS + cutover del Kanban a `/api/v1/applications`.
- **R17/R18** — extensión de captura de ofertas + recomendaciones ESCO en Home;
  loop skill-gap → plan de objetivos.

## 🧹 Deuda técnica menor conocida

- `RuntimeWarning: coroutine 'Redis.close' was never awaited` al apagar
  (`main.py` shutdown).
- `mcp_server` readiness check: "advisory: unhandled errors in a TaskGroup".
- pytest no viene en la imagen del backend: instalar con pip (user-site) y
  ejecutar con `PYTHONPATH=/app/.local/lib/python3.13/site-packages`.
