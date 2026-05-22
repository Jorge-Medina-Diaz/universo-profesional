---
sector: data_eng
slug: data_eng/pipelines
title: "Pipelines de datos: orquestación, idempotencia, backfills"
subtitle: "Cómo se mueve data entre sistemas sin sustos"
tags: [airflow, dagster, prefect, dbt, etl, elt, idempotency, backfill, lineage]
weight: high
audience_levels: [mid, senior, staff]
when_to_ask:
  - "el usuario menciona Airflow, Dagster, Prefect, dbt, pipelines"
  - "habla de ETL/ELT, batch, backfills"
  - "describe lineage, orchestration, data quality"
---

## Criterios clave

- **Idempotencia por defecto**: cada task debe poder re-correrse sin efecto colateral. Output writes a temp + atomic rename, o delete-insert por partición.
- **Particionado temporal**: jobs procesan `date` partitions explícitamente. Backfills = `airflow backfill --start-date X --end-date Y`, no scripts ad-hoc.
- **Dependency-as-code**: el DAG es un dato (Airflow, Dagster, Prefect). Triggers basados en datasets (Dagster) > cron + skip if upstream missing.
- **Data quality como gate**: dbt tests, Great Expectations, Soda. Falla rompe el pipeline, no se cataloga después.
- **Lineage observable**: qué tabla viene de qué pipeline, qué jobs la consumen. Marquez, OpenLineage, dbt docs, Atlan.
- **SLOs por dataset**: "tabla X actualizada antes de las 09:00 GMT con 99% de días". Si rompes, alerta + runbook.
- **Reprocessing strategies**: sin sobre-escribir histórico; versionar con `processed_at` o snapshot tables. Reproducibilidad > optimización temprana.

## Preguntas guía

- "¿Tus tasks son idempotentes? ¿Cómo lo garantizas?"
- "¿Cómo manejas backfills? ¿Has hecho uno grande recientemente?"
- "¿Qué herramienta de orquestación usas y por qué (Airflow, Dagster, Prefect)?"
- "¿Cómo testeas la calidad de los datos? ¿Qué pasa cuando falla?"
- "¿Tienes lineage observable end-to-end?"
- "¿SLOs de freshness de datasets? Cuéntame."

## Señales de seniority

- **Mid**: Airflow DAGs básicos, dbt con algunos tests, conoce ETL clásico.
- **Senior**: idempotencia disciplinada, particionado consciente, dbt tests + macros, alerting de SLO de freshness, ha gestionado backfills grandes.
- **Staff/Principal**: arquitectura de datos org-wide (medallion, data mesh), governance de schema changes, observabilidad de lineage, cost-awareness en warehouse (BigQuery/Snowflake bills), contract-driven data.

## Anti-patterns

- Tasks que escriben directo a la tabla final sin atomic swap → estados inconsistentes durante fail.
- `now()` dentro de un job → no reproducible.
- "Si falla, reintenta" sin idempotencia → datos duplicados.
- Bridging Airflow + cron + scripts manuales → caos.
- Tests post-hoc en BI tools en lugar de gates en pipeline.
- Sin tags ni lineage → "no sabemos qué consume X".
- `SELECT *` en SQL de producción → schema changes rompen silenciosamente.

## Recursos

- *Fundamentals of Data Engineering* — Joe Reis & Matt Housley.
- *The Data Warehouse Toolkit* — Ralph Kimball (modelado dimensional).
- dbt docs (especialmente macros + tests).
- Dagster docs (software-defined assets > task-based DAGs).
- *Designing Data-Intensive Applications* — Kleppmann.
- Locally Optimistic blog (data engineering en startups reales).
- *Reverse ETL* readings (Hightouch, Census).
