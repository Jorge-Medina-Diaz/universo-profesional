---
sector: devops
slug: devops/reliability_sre
title: "Reliability / SRE: SLOs, incident response, postmortems, chaos"
subtitle: "Lo que distingue a un equipo que ARDE cada noche del que sale a las 18h"
tags: [sre, slo, sli, error-budget, incident, postmortem, runbook, chaos]
weight: high
audience_levels: [mid, senior, staff, principal]
when_to_ask:
  - "el usuario menciona SRE, SLO, SLI, error budget, on-call"
  - "habla de incident response, postmortem, runbook, chaos engineering"
  - "describe culture blameless o paging policy"
---

## Criterios clave

- **SLI/SLO/SLA explícitos**: cada servicio tier-0/1 tiene SLIs (availability, latency p99, error rate) traducidos a SLO (target %). SLA es el contrato con el cliente (más laxo que SLO interno).
- **Error budget como herramienta de negocio**: si gastaste tu budget de 0.1% downtime → freeze de features hasta recuperar. Comunicado a producto, no escondido.
- **Incident response procedimentado**: severity levels (SEV1-SEV4) claros. Incident commander asignado. Comms channel dedicado. Status page actualizada. Customer comms en SEV1/2.
- **Postmortem blameless obligatorio en SEV1/2**: timeline, root cause (5-whys), action items con owner + due date. Compartido públicamente en la org. NO se cierra hasta que las actions están done.
- **Runbooks ejecutables**: cada alerta crítica linka a un runbook con pasos verificados. Idealmente automatizado (auto-remediation).
- **On-call humano**: rotación de 1 semana, max 5h/semana de paging activo. Compensation (free time / bonus). Onboarding before primary.
- **Chaos engineering proactivo**: GameDays mensuales/trimestrales. Failure injection en pre-prod. "Wheel of Misfortune" para entrenar.
- **Observability triada**: logs estructurados + metrics + traces. SLO dashboard visible. Alert rules → only paging actionable signals.

## Preguntas guía

- "¿Tienes SLOs definidos? ¿Cómo decidiste los targets?"
- "¿Cuál fue tu último error budget burn? ¿Qué hizo el equipo?"
- "Cuéntame del último SEV1 que tuviste — cómo fue la respuesta y el postmortem."
- "¿Quién carga la pager esta semana? ¿Cuántos pages activos por semana en promedio?"
- "¿Tenéis GameDays? ¿Cuándo fue el último y qué encontrasteis?"
- "¿Tus alertas pagean cosas accionables o ruido?"

## Señales de seniority

- **Mid**: hace on-call, sigue runbooks, escribe alertas razonables, contribuye a postmortems.
- **Senior**: define SLOs por servicio, lidera postmortems, escribe runbooks, lleva GameDays. Compone burn-rate alerts (no solo threshold).
- **Staff/Principal**: define la práctica SRE a nivel org, balanza reliability vs velocity con producto, instaura blameless culture, mide DORA + SPACE + reliability juntos. Negocia error budget con stakeholders.

## Anti-patterns

- SLAs sin SLOs internos → te enteras del downtime por el cliente.
- Postmortems con blame ("X causó esto") → la gente esconde info la próxima vez.
- On-call rotación de 1-2 personas → burnout garantizado.
- Alertas que pagean cosas que no son accionables ("disk > 70%") → alert fatigue.
- "Chaos engineering" sin pre-prod realista → solo PR theatre.
- Status page actualizada manualmente después del incidente.
- Runbooks teóricos que nadie ha ejecutado → primera vez bajo presión = desastre.

## Recursos

- "Site Reliability Engineering" (Google, libro 1) — origen de la disciplina.
- "Site Reliability Workbook" (Google, libro 2) — más práctico.
- "Implementing Service Level Objectives" — Alex Hidalgo.
- PagerDuty's postmortem template (de las mejores referencias).
- Chaos Toolkit + Gremlin + Litmus para chaos eng.
- Charity Majors' blog (honeycomb.io) sobre observability.
