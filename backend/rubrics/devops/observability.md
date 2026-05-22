---
sector: devops
slug: devops/observability
title: "Observabilidad ops: monitoring, alerting, on-call"
subtitle: "Hacer que un servicio sea operable por humanos a las 3am"
tags: [monitoring, prometheus, grafana, alerting, on-call, slo, datadog]
weight: high
audience_levels: [junior, mid, senior, staff]
when_to_ask:
  - "el usuario menciona Prometheus, Grafana, Datadog, monitoring, alertmanager"
  - "habla de on-call, paging, incident response"
  - "describe SLOs/SLIs, error budgets"
---

## Criterios clave

- **Three pillars**: logs (structured + central), metrics (Prometheus/Datadog), traces (OpenTelemetry). Cada uno con casos de uso distintos; no son intercambiables.
- **SLOs antes que dashboards**: define qué significa "sano" (99.9% requests < 500ms con < 0.5% error). Lo demás es decoración.
- **Alerting on symptoms**: page cuando algo duele al usuario; warn cuando se acerca. CPU al 90% no es síntoma, es síntoma de algo que sí.
- **Runbook por alert**: la alerta dice "qué pasa", el runbook dice "qué hacer". Sin runbook, no hay alerta.
- **On-call rotation humana**: rotación clara, hand-off documentado, escalation policy. Nadie hace on-call solo. Comp por on-call (tiempo o dinero).
- **Postmortems blameless**: cada incidente significativo tiene postmortem en 1 semana. Action items con owners + deadlines.
- **Error budget como contrato**: si se quema, freeze de releases hasta recuperar. No es opcional.

## Preguntas guía

- "¿Qué SLOs tenéis y cómo los mediste/decidiste?"
- "Cuéntame de un incidente reciente — ¿cómo se detectó, cómo se resolvió, qué aprendisteis?"
- "¿Cómo es vuestra rotación de on-call? ¿Cuántos paging por semana?"
- "¿Alertáis por síntoma o por causa? Dame un ejemplo."
- "¿Habéis quemado el error budget alguna vez? ¿Qué hizo el equipo?"
- "¿Cómo correlacionas logs con traces con métricas?"

## Señales de seniority

- **Junior**: mira dashboards pre-hechos, reacciona a alertas.
- **Mid**: crea dashboards propios, configura algunas alertas, conoce SLO de oídas.
- **Senior**: define SLOs basados en CUJ (critical user journeys), escribe runbooks, instrumenta nuevas features con métricas RED + traces, ha sido on-call y mejorado el sistema desde la experiencia.
- **Staff/Principal**: gobierna la estrategia de observability (cost, retention, cardinalidad), modela error budgets, evangeliza blameless postmortems, mide DORA metrics + MTTD/MTTR como KPIs del equipo.

## Anti-patterns

- "Todo es importante, todo es P1" → fatiga, las verdaderas se ignoran.
- Alertas a Slack canal compartido sin paging real → nadie responde.
- Dashboard wall con 50 paneles que nadie revisa.
- Métricas con `user_id` como label → cardinalidad explota, billing surprise.
- Postmortem que culpa a una persona — no hay aprendizaje.
- Logs sin trace_id → debugging post-mortem es imposible.
- On-call sin compensación ni rotación → burnout.

## Recursos

- *Site Reliability Engineering* y *The SRE Workbook* — Google. Gratis online.
- Google's *Site Reliability Workbook* capítulos sobre alerting + on-call.
- *Implementing Service Level Objectives* — Alex Hidalgo.
- Charity Majors blog + *Observability Engineering* (O'Reilly).
- Honeycomb learning resources.
- PagerDuty Incident Response docs.
- IncidentLabs / Rootly playbooks.
