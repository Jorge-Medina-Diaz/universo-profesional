---
sector: devops
slug: devops/iac
title: "Infraestructura como código (Terraform, Pulumi, CDK)"
subtitle: "Cómo se gestiona infra reproducible y sin sustos"
tags: [iac, terraform, pulumi, cdk, ansible, drift, modules]
weight: high
audience_levels: [junior, mid, senior, staff]
when_to_ask:
  - "el usuario menciona Terraform, Pulumi, CDK, Ansible, IaC"
  - "habla de provisioning, infra reproducible, multi-env"
  - "describe drift detection o gestión de state"
---

## Criterios clave

- **State remoto + locking**: nunca state local en disco. S3+DynamoDB (Terraform), Pulumi Cloud, Spacelift, Terraform Cloud, etc. Locking previene corrupciones.
- **Módulos reutilizables** con interfaces claras (inputs/outputs documentados). Versionado semántico de módulos. Separar "stacks" (deployable units) de "modules" (building blocks).
- **Multi-env** (dev/staging/prod) con isolation real: cuentas/proyectos cloud separados > workspaces compartidos. Diffs entre envs visibles y revisables.
- **Plan obligatorio antes de apply** en CI. Apply manual o auto-aprobado con guardrails (drift detection, policy-as-code OPA/Sentinel).
- **Drift detection** programada (e.g. `tflint` + `tfsec` + `tf plan` diario). Cambios fuera-de-IaC son una alarma, no la norma.
- **Secretos fuera del state**: AWS SSM, Vault, sealed-secrets. Nunca `default = "supersecret"`.
- **Tests** con `terratest` o `pulumi-policy-as-code`. Smoke tests post-apply (health endpoint, DB connection).

## Preguntas guía

- "¿Dónde guardas el state? ¿Cómo gestionas el locking?"
- "¿Cómo separas dev/staging/prod? ¿Workspaces, cuentas, módulos?"
- "Cuéntame del último drift que detectaste — ¿cómo lo reconciliaste?"
- "¿Cuándo apply manual vs automático? ¿Qué guardrails tienes?"
- "¿Has refactorizado un módulo grande (state moves, imports)? Cuéntame."
- "¿Cómo gestionas los secretos en IaC?"

## Señales de seniority

- **Junior**: corre `terraform apply` en local con state local. Sabe lo que es un módulo.
- **Mid**: state remoto, workspaces para envs, módulos propios reusables, plan en CI.
- **Senior**: drift detection automatizada, policy-as-code (OPA/Sentinel), gestión de secretos correcta, refactor de state (`terraform state mv`, imports) hecho con cuidado, multi-account/multi-project.
- **Staff/Principal**: governance del IaC estate, define convenciones org-wide, propulsa golden modules, gestiona migraciones grandes (Terraform → OpenTofu, monorepo IaC), trabajo con FinOps + security para guardrails.

## Anti-patterns

- State local committed al repo.
- `terraform apply` directo en prod sin plan revisado.
- Modificar recursos en consola cloud sin actualizar IaC → drift permanente.
- Módulos con 30 inputs y sin documentación.
- "Una sola root module gigante" sin separación de blast radius.
- Secrets en `terraform.tfvars` committed.
- No tener `terraform state` backup antes de operaciones destructivas.

## Recursos

- *Terraform Up & Running* — Yevgeniy Brikman.
- HashiCorp Learn (oficial, muy bueno).
- *The DevOps Handbook* — Gene Kim. Más amplio, pero contextualiza el porqué.
- Pulumi docs (modelo programático bien explicado).
- Terragrunt docs para multi-env y DRY config.
- OPA/Sentinel docs para policy-as-code.
