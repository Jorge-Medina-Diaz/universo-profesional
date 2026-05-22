---
sector: general
slug: general/technical_writing
title: "Technical writing: ADRs, runbooks, API docs, blog strategy"
subtitle: "Lo que distingue a un IC senior de uno staff: documentación que escala el conocimiento"
tags: [writing, adr, runbook, api-docs, rfc, blog, documentation]
weight: medium
audience_levels: [senior, staff, principal]
when_to_ask:
  - "el usuario menciona ADRs, RFCs, runbooks, documentation"
  - "habla de internal blog, eng blog, content strategy"
  - "describe cómo el equipo escala conocimiento"
---

## Criterios clave

- **ADRs versionados en repo**: cada decisión arquitectónica importante = 1 markdown con context/decision/consequences/status. Buscables, vinculables. No mueren en Confluence.
- **Runbooks ejecutables**: cada alerta crítica linka a un runbook con pasos verificados. Idealmente con scripts ejecutables (no solo prosa).
- **API docs vivos**: OpenAPI / AsyncAPI generados desde el código, no escritos a mano. Linked desde el repo del servicio. Versionados con la API.
- **RFCs para cambios grandes**: > 1 semana de trabajo = RFC. Template fijo (motivation, proposal, alternatives, drawbacks, unresolved questions). Review por escrito antes de coding.
- **Onboarding docs**: nuevo dev productivo en 1 semana. README ejecutable. Glossary del dominio.
- **Blog público o interno**: cada postmortem importante + decisiones grandes + lessons learned → 1 post. Construye marca personal + comparte conocimiento.
- **Audiencia clara en cada doc**: ¿es para devs nuevos? ¿para on-call? ¿para producto? ¿para customers? La voz cambia.

## Preguntas guía

- "¿Tu equipo tiene ADRs / RFCs versionados? ¿Cuántos y revisitados?"
- "Cuéntame del último runbook que escribiste — ¿lo ejecutó alguien sin tu ayuda?"
- "¿Tienes blog (interno o público)? ¿Cuándo fue el último post?"
- "¿Cómo onboardas nuevos devs? ¿En cuánto tiempo son productivos?"
- "¿Qué documento de los que escribes es el que más impacto tiene?"

## Señales de seniority

- **Mid**: escribe READMEs decentes, contribuye runbooks cuando los pide on-call.
- **Senior**: escribe ADRs/RFCs por defecto en decisiones importantes, mantiene runbooks ejecutables, hace internal blog posts.
- **Staff/Principal**: establece templates org-wide, mentora otros en writing, escribe en blog público, su escritura mueve decisiones a nivel org. Mide impacto.

## Anti-patterns

- Docs en Confluence sin owner → mueren en 6 meses.
- READMEs auto-generados sin contexto → "para arrancar haz `npm install`" sin decir qué es el proyecto.
- ADRs sin status lifecycle → quedan obsoletos sin marcar.
- Runbooks que asumen contexto que el on-call no tiene a las 3am.
- "Documentaremos cuando tengamos tiempo" → nunca.
- Blog post genérico sin ángulo propio → no aporta, no se comparte.

## Recursos

- "Docs for Developers" — Jared Bhatti et al.
- arc42 template para documentación arquitectónica.
- Squarespace's RFC template (público).
- PagerDuty's runbook template.
- Will Larson's blog (staffeng.com) — referente en eng writing.
- Julia Evans (jvns.ca) — calidad de explicación.
