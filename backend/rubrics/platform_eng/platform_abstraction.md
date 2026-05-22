---
sector: platform
slug: platform_eng/platform_abstraction
title: "Platform abstraction: Backstage, Pulumi automation API, multi-tenancy"
subtitle: "Cómo construir la abstracción correcta sin esconder lo que importa"
tags: [backstage, idp, pulumi, crossplane, terragrunt, multi-tenancy, governance]
weight: medium
audience_levels: [senior, staff, principal]
when_to_ask:
  - "el usuario menciona Backstage, Crossplane, Pulumi automation API, Terragrunt"
  - "habla de internal developer platform (IDP), abstraction layers"
  - "describe multi-tenancy o gobernance de plataforma"
---

## Criterios clave

- **Abstraction at the right level**: la plataforma debe exponer "service" o "database", no "Pod" o "RDS instance". Pero NO esconder los SLOs ni el coste. Devs deben saber qué garantizan.
- **APIs declarativas**: el contrato es un YAML/HCL (no un ticket). Crossplane (K8s-native) o Pulumi/Terraform módulos opinionados. CUE / Dhall si necesitas validación fuerte.
- **Multi-tenancy**: separación de namespaces, network policies, RBAC, secrets por tenant. No "todos comparten el mismo K8s sin reglas".
- **Governance**: Open Policy Agent (Gatekeeper) o Kyverno para policies en K8s. Conftest en CI. Cada policy con escape hatch documentado.
- **Lifecycle de la plataforma**: versionado de la API que exponéis a devs. Deprecation calendar (>6 meses notice). Migrations automatizadas cuando es posible.
- **Observabilidad de la plataforma misma**: medís reliability de tu API (deploy time p99, success rate). Las propias métricas que pides a tus consumidores.
- **Documentación viva**: ADRs públicos, runbooks ejecutables, demos grabadas, changelog visible.

## Preguntas guía

- "¿Qué abstracción expone tu platform — Service, Application, otra? ¿Por qué ese nivel?"
- "¿Cómo aplicáis policies — OPA, Kyverno, ad-hoc?"
- "Cuéntame de una migración disruptiva que la plataforma manejó bien (o mal)."
- "¿Tenéis SLOs de la propia plataforma? ¿Los publicáis?"
- "¿Cómo gestionáis tenants con requisitos distintos (uno necesita PCI, otro no)?"

## Señales de seniority

- **Mid**: opera la plataforma existente, contribuye módulos.
- **Senior**: diseña abstracción nueva, balanza opinionado vs flexible, lifecycle versioning, multi-tenancy básico.
- **Staff/Principal**: estrategia "build vs buy" justificada, lleva governance multi-org, decide entre Crossplane vs Pulumi vs Backstage por trade-offs reales, mentoriza otros platform leads.

## Anti-patterns

- Abstracción que esconde el coste o el blast radius → devs sin contexto toman decisiones malas.
- Plataforma sin versioning → cada change rompe alguien sin aviso.
- "Multi-tenancy" que es solo namespaces sin network policies → un tenant DoS al resto.
- Backstage como catálogo de software desactualizado (peor que no tenerlo).
- "Build everything" cuando Crossplane / Pulumi / Backstage cubren el 80%.
- Policies sin escape hatch documentado → frustration y workarounds informales.

## Recursos

- Backstage docs + Spotify engineering blog.
- Crossplane docs ("compose your own platform API").
- Pulumi automation API docs (programmatic IaC).
- "Building Internal Platforms" (talks de Manuel Pais, Camille Fournier).
- OPA / Gatekeeper / Kyverno comparison resources.
- KubeCon talks de "Platform Engineering" track.
