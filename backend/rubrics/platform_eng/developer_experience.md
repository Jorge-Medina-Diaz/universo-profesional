---
sector: platform
slug: platform_eng/developer_experience
title: "Developer Experience: golden paths, self-service, DX metrics"
subtitle: "Cómo hacer que el equipo entregue rápido sin reinventar la rueda cada sprint"
tags: [dx, platform, golden-path, self-service, dora, spotify, backstage]
weight: high
audience_levels: [senior, staff, principal]
when_to_ask:
  - "el usuario menciona platform team, DX, IDP, golden paths, self-service"
  - "habla de DORA metrics, lead time, MTTR, deploy frequency"
---

## Criterios clave

- **Golden paths**: 1-3 caminos opinionados (ej. "nuevo microservicio Python" o "nuevo frontend Next.js") con scaffolding completo (CI, deploy, observabilidad, healthchecks). El developer crea el proyecto y arranca en producción en <2h.
- **Self-service infra**: equipos crean DBs, colas, buckets vía portal/CLI sin tickets a SRE. Quotas + presets seguros (encryption, backup, monitoring) por defecto.
- **DX metrics**: DORA (deploy freq, lead time for changes, MTTR, change failure rate) + SPACE (satisfaction, performance, activity, communication, efficiency). Survey developers cada 6 meses.
- **Tooling distribution**: docs centralizadas (Backstage / similar). Onboarding guiado <1 día. Versionado de templates (no break sin migration guide).
- **Standards as code**: linters/formatters obligatorios en CI, secret scanning, dependency scanning, SBOM generation.
- **Service catalog**: ownership map de cada microservicio. SLO declarados. On-call rotation explícita. Dependency graph visible.
- **Cost transparency**: cada team ve su gasto en cloud en tiempo near-real-time. Showback (no chargeback) educativo.

## Preguntas guía

- "¿Tenéis golden paths definidos? ¿Cuántos y cuántos equipos los usan?"
- "¿Cómo medís DX? DORA, SPACE, otra cosa?"
- "Cuéntame el último survey de developers — ¿qué les frustraba más?"
- "¿Qué proporción de tareas requieren ticket a platform team vs son self-service?"
- "¿Tenéis service catalog? ¿Quién mantiene los metadata?"

## Señales de seniority

- **Junior**: usa el platform pero no opina. Sabe seguir el golden path.
- **Mid**: detecta fricción en golden paths, propone fixes. Contribuye plantillas. Conoce DORA y por qué importan.
- **Senior**: diseña golden paths con balance entre opinionated y flexible. Mide adopción. Lleva surveys.
- **Staff/Principal**: define platform strategy de la empresa. Decide build vs buy (Backstage vs comercial). Garantiza alignment producto ↔ platform ↔ SRE. Promociona la práctica fuera.

## Anti-patterns

- Platform team que solo escribe código de infra sin hablar con devs.
- Golden paths inmutables — cada change requiere fork → fragmentación.
- Backstage instalado pero vacío (service catalog desactualizado = peor que nada).
- Métricas vanity (cuántos servicios desplegados) en lugar de DX outcomes.
- "Self-service" que en realidad es "rellena este YAML y pásalo a platform team".
- Chargeback agresivo antes de showback educativo → resistencia política.

## Recursos

- "Team Topologies" — Matthew Skelton & Manuel Pais.
- "Accelerate" — Nicole Forsgren et al (origen DORA).
- Spotify engineering blog (origen Backstage).
- Platform Engineering community + DevEx con Abi Noda.
- "The DevOps Handbook" — Gene Kim et al.
