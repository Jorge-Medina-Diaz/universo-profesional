---
sector: cloud
slug: cloud/azure_services
title: "Azure — App Service, Functions, AKS, Cosmos, Entra ID"
subtitle: "Azure brilla en empresa enterprise + integración con AD/Entra"
tags: [azure, app-service, functions, aks, cosmos-db, entra-id, devops]
weight: medium
audience_levels: [mid, senior, staff]
when_to_ask:
  - "el usuario menciona Azure, AKS, App Service, Functions, Cosmos, Entra"
  - "habla de integraciones con Microsoft 365 / Active Directory"
---

## Criterios clave

- **Identity-first**: Entra ID (antes Azure AD) como IDP. Managed Identities en lugar de credenciales. RBAC con scope correcto (Subscription / Resource Group / Resource). Conditional Access policies.
- **Compute**: App Service para web apps clásicas (deploy slots para canary). Container Apps / Functions para serverless. AKS para K8s con integración fuerte de Entra. AVMs (Azure Virtual Machines) cuando hay legacy.
- **Datos**: Cosmos DB para NoSQL global (elige consistency level correcto, RU optimization). Azure SQL para SQL gestionado. Storage Accounts con tiers (hot/cool/archive).
- **Eventos**: Event Grid (push), Service Bus (queues + topics enterprise), Event Hubs (streaming volumen).
- **Observabilidad**: Application Insights + Log Analytics + Azure Monitor + Workbooks dashboards.
- **Gobernance**: Management Groups → Subscriptions → Resource Groups jerarquía. Azure Policy para enforcement. Cost Management + Budgets.
- **DevOps**: Azure DevOps (Repos+Pipelines+Boards) o GitHub Actions con OIDC contra Entra ID.

## Preguntas guía

- "¿Por qué Azure — alineación con stack Microsoft, customer demand, otro?"
- "¿Entra ID con Managed Identities o aún usas service principals con secret?"
- "¿AKS, App Service, Container Apps, o Functions? ¿Cómo elegiste?"
- "¿Cosmos DB con qué consistency level y por qué? ¿Cómo controlas el coste de RUs?"
- "¿Has integrado pipelines de Azure DevOps con políticas de Entra?"

## Señales de seniority

- **Junior**: App Service deploys, conoce Storage Accounts, usa portal o az CLI.
- **Mid**: AKS básico, RBAC + Managed Identities, ARM/Bicep templates, App Insights queries.
- **Senior**: Landing Zones de Microsoft Cloud Adoption Framework, Azure Policy enforcement, Cosmos optimization (RUs + partition key correcto), Entra Conditional Access.
- **Staff/Principal**: Multi-subscription governance, Azure Lighthouse para MSPs, enterprise integration (M365, Power Platform), FinOps con cost management gobernance.

## Anti-patterns

- Service Principals con secret de larga vida en lugar de Federated Credentials.
- Cosmos DB con consistency `Strong` cuando no se necesita (10× coste de RUs).
- App Service Plan compartido entre prod y dev sin restricciones.
- ARM templates jurassic-style en lugar de Bicep (mucho más legible).
- Subscriptions múltiples sin Management Groups → governance imposible.
- Sin Azure Policy → drift configuracional incontrolable.

## Recursos

- Microsoft Cloud Adoption Framework + Azure Architecture Center.
- "Azure Well-Architected Framework" docs.
- Bicep playground + Microsoft Learn paths.
- Microsoft Ignite recorded sessions.
- Charles Lamanna's blog (Azure leadership perspective).
