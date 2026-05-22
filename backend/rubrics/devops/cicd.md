---
sector: devops
slug: devops/cicd
title: "CI/CD: pipelines, environments, gating, deploys"
subtitle: "Cómo se mueven cambios de commit a producción sin sustos"
tags: [cicd, github-actions, gitlab-ci, argocd, canary, blue-green, artifacts]
weight: high
audience_levels: [junior, mid, senior, staff]
when_to_ask:
  - "el usuario menciona CI/CD, GitHub Actions, GitLab CI, Jenkins, ArgoCD"
  - "habla de deploys, releases, canary, blue-green"
  - "describe gates de calidad o promotion entre envs"
---

## Criterios clave

- **Pipeline por commit**: lint + typecheck + unit tests + build en cada PR. Verde obligatorio para merge.
- **Artefactos inmutables**: docker images con tag SHA (no `latest`). Mismo artefacto sube por dev→staging→prod, no se rebuilea por env.
- **Promote, no rebuild**: el deploy a prod es promote del artefacto que pasó staging. Cualquier rebuild rompe la cadena de confianza.
- **Environments con gating**: prod requiere approval manual o test post-deploy verde. Staging puede ser auto-promote tras dev verde.
- **Estrategia de release**: canary (1% → 10% → 50% → 100%) o blue-green. Rollback en un comando (idealmente automático tras error rate spike).
- **Migrations en deploy seguro**: expand-contract; nunca migration breaking + code change en mismo deploy.
- **Secrets en CI**: vault o cloud secret manager. Nunca en YAML committed. Audit log de quién ve qué.
- **Smoke tests post-deploy**: health endpoint, login flow, query crítica de BD. Si falla → rollback automático.

## Preguntas guía

- "¿Cómo es tu pipeline desde commit a prod? Cuéntame las etapas."
- "¿Tienes artefactos inmutables o se rebuilea por env?"
- "¿Cómo haces releases — canary, blue-green, big-bang? Por qué?"
- "Cuéntame de un rollback que tuviste que hacer — ¿cómo de rápido fue?"
- "¿Cómo gestionas migrations de DB junto con deploys?"
- "¿Qué smoke tests corren post-deploy?"

## Señales de seniority

- **Junior**: pipeline básico (tests + build). Deploy manual desde laptop.
- **Mid**: deploys auto a dev/staging con tests, manual gate a prod, conoce artifact registry.
- **Senior**: artefactos inmutables con promotion, canary/blue-green, smoke tests post-deploy, runbook de rollback, migrations expand-contract.
- **Staff/Principal**: define la deploy strategy org-wide (GitOps con ArgoCD/Flux, feature flags), gestiona release cadence + change windows, propulsa deploys más frecuentes con menor riesgo (DORA metrics: lead time, deploy freq, MTTR, change failure rate).

## Anti-patterns

- `docker push myimage:latest` y `docker pull latest` en prod → no sabes qué SHA corre.
- "Build in prod" — el CI no compila para staging y prod por separado.
- Deploy a prod sin tests post-deploy → te enteras del breakage por usuarios.
- Migrations en mismo PR que cambio de código que las requiere → rollback imposible.
- Secrets en `.env` committed (incluso "solo para staging").
- Pipeline que tarda 45min porque corre todo en serial.
- Deploys de viernes a las 17:00.

## Recursos

- *Accelerate* — Forsgren, Humble, Kim. Métricas DORA en profundidad.
- *Continuous Delivery* — Humble & Farley (libro fundacional).
- GitHub Actions docs (matrices, environments, OIDC).
- ArgoCD docs (GitOps).
- *Database Reliability Engineering* — Campbell & Majors (capítulo sobre migrations).
- Charity Majors blog (deploys frecuentes + observabilidad).
