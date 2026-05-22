---
sector: backend
slug: backend/observability
title: "Observabilidad backend: logs, traces, métricas, SLOs"
subtitle: "Qué hace que un servicio sea operable en producción"
tags: [logging, tracing, metrics, slo, opentelemetry, prometheus, alerts]
weight: high
audience_levels: [junior, mid, senior, staff]
when_to_ask:
  - "el usuario menciona logs, métricas, traces, observabilidad"
  - "describe un incidente o debugging en producción"
  - "habla de SLOs, alertas, monitoring, on-call"
---

## Criterios clave

- **Structured logging** (JSON) con campos canónicos: `timestamp`, `level`, `request_id`/`trace_id`, `user_id` (hash si hay PII), `route`, `duration_ms`. Nunca `print()` o strings.
- **Distributed tracing** con OpenTelemetry: span por request HTTP + por dependencia externa (DB, caches, otros servicios). Sampling configurable (1-10% en prod, 100% en errores).
- **Métricas RED + USE**: RED (Rate, Errors, Duration) por endpoint. USE (Utilization, Saturation, Errors) por recurso (CPU, memoria, DB connections).
- **SLOs por servicio**: 99% de requests < 500ms; 99.9% de éxito (no 5xx). Error budget mensual. Cuando se quema, freeze de features.
- **Alerts on symptoms, not causes**: alerta cuando los usuarios duelen ("p99 latency > 2s"), no cuando una métrica interna pasa un umbral arbitrario ("CPU > 70%").
- **Runbooks por alert**: cada alerta enlaza a un runbook con "qué mirar, qué probar, cómo escalar".
- **Cardinalidad controlada**: ojo con etiquetas dinámicas (user_id, request_id) en métricas Prometheus — explotan el storage.

## Preguntas guía

- "¿Tu logging es estructurado? ¿Qué campos canónicos?"
- "¿Usas trace IDs cross-service? ¿Cómo correlacionas logs con traces?"
- "¿Tienes SLOs por servicio? ¿Cómo decides el target?"
- "Cuéntame del último incidente — ¿cómo lo detectaste, cómo lo diagnosticaste?"
- "¿Cómo decides qué alertas crear y cuáles silenciar?"
- "¿Has tenido alguna vez una cardinalidad explosiva en métricas? ¿Cómo lo arreglaste?"

## Señales de seniority

- **Junior**: logs como strings, métricas básicas (request count). Conoce dashboards Grafana de alguien.
- **Mid**: structured logging, request_id en logs, dashboards propios por feature, métricas Prometheus básicas. Quizás un poco de tracing.
- **Senior**: OpenTelemetry end-to-end, RED metrics por endpoint, SLOs documentados, runbooks por alert, ha vivido al menos un incidente serio que le marcó.
- **Staff/Principal**: define la estrategia de observabilidad de la org, gestiona error budgets, modela cardinalidad y cost (alta visibilidad sale caro), implementa proxy de profile/heap dumps, define oncall culture.

## Anti-patterns

- Logging `print("user did X")` sin level ni structured fields.
- Alertas por CPU o memoria absolutos → ruido. Alertas deberían ser por impacto al usuario.
- Métricas con `user_id` o `request_id` como label → cardinalidad explosiva, billing surprise.
- Runbook = "consulta al senior de turno" → no es runbook.
- Logs que contienen el body completo de requests, incluyendo passwords/tokens.
- "El log file local es fuente de verdad" — sin agregación centralizada (Loki, ELK, Datadog), debugging post-mortem es imposible.
- Dashboards de 50 paneles que nadie revisa.

## Recursos

- *Distributed Systems Observability* — Cindy Sridharan (ebook gratis O'Reilly).
- *Site Reliability Engineering* y *The SRE Workbook* — Google. Gratis online.
- OpenTelemetry docs (modelo de spans, propagación).
- Prometheus best practices oficiales (naming, labels, cardinality).
- Honeycomb blog (high-cardinality observability).
- Grafana docs sobre alerting strategies.
