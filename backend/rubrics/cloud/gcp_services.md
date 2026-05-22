---
sector: cloud
slug: cloud/gcp_services
title: "GCP — Cloud Run, GKE, BigQuery, Pub/Sub, IAM"
subtitle: "GCP shines en data + serverless; el ecosistema IAM es el más opinionado de los 3"
tags: [gcp, cloud-run, gke, bigquery, pubsub, iam, dataflow, vertex-ai]
weight: high
audience_levels: [mid, senior, staff]
when_to_ask:
  - "el usuario menciona GCP, Cloud Run, GKE, BigQuery, Pub/Sub, Vertex AI"
  - "habla de data warehousing o ML platform en cloud"
---

## Criterios clave

- **IAM granular GCP-style**: Project ↔ Folder ↔ Organization hierarchy. Service accounts con keys rotation o (mejor) Workload Identity Federation. NO mezclar roles primitivos (`roles/owner`) con predefinidos sin querer.
- **Compute**: Cloud Run para containers serverless (1ª opción). GKE para K8s real (Autopilot si no quieres operar el plano). App Engine solo legacy. Compute Engine cuando necesitas SO control.
- **Datos**: BigQuery es la corona — separar storage de compute, slots reservados vs on-demand, materialized views, partitioning + clustering. Cloud Storage con lifecycle. Spanner si necesitas SQL globalmente consistente.
- **Eventos/pipelines**: Pub/Sub (push o pull), Dataflow para streams + batch (Apache Beam), Cloud Composer (managed Airflow).
- **ML platform**: Vertex AI integra entrenamiento + serving + experiments + pipelines. AutoML para baseline. Custom training con containers.
- **Observabilidad**: Cloud Logging + Cloud Monitoring + Cloud Trace + Error Reporting (suite todo-en-uno bastante mejor integrada que AWS).
- **Coste**: Committed Use Discounts (CUDs) para baseline. Sustained Use Discounts automáticos. BigQuery slot reservation si volumen alto.

## Preguntas guía

- "¿Por qué GCP y no AWS / Azure para tu caso?"
- "¿Cloud Run o GKE? ¿Por qué?"
- "¿Cómo manejas costes en BigQuery — slots, on-demand, partitioning?"
- "¿Tienes Workload Identity Federation o aún usas keys JSON?"
- "¿Has trabajado con Vertex AI / Dataflow en pipelines reales?"

## Señales de seniority

- **Junior**: usa la consola, conoce Cloud Run + Cloud Storage + BigQuery básico (queries).
- **Mid**: pipelines Dataflow simples, GKE con Autopilot, IAM roles predefinidos correctos, observabilidad con Cloud Monitoring.
- **Senior**: BigQuery optimization (slot reservation, clustering), Workload Identity Federation, VPC Service Controls, Organization Policy.
- **Staff/Principal**: governance multi-project con Folders, gestión de costes a nivel org, ML platform desde Vertex AI a producción, decisiones de migración entre clouds.

## Anti-patterns

- Service account keys como JSON files en disco (deberían ser WIF).
- BigQuery on-demand sin entender que cuesta $5/TB scanned — sin partitioning truena el bill.
- Usar `roles/owner` en service accounts "porque no funcionaba".
- App Engine Standard como caja negra: cuando crece se vuelve impagable migrar.
- GKE Standard sin entender plano de control (auto-upgrade off, surprise nodes upgrade rompe).
- "Hago todo en Cloud Console" — sin IaC = sin reproducibilidad.

## Recursos

- Google Cloud Architecture Framework (análogo al Well-Architected de AWS).
- "Data Engineering on GCP Specialization" (Coursera).
- BigQuery best practices docs.
- "Site Reliability Engineering" (Google's book — origen del término).
- GCP Next talks (BigQuery + Vertex AI son siempre las joyas).
