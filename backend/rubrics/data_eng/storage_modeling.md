---
sector: data_eng
slug: data_eng/storage_modeling
title: "Storage y modelado: warehouse, lakehouse, schema design"
subtitle: "Decisiones que determinan si tu data layer escala o ahoga al negocio"
tags: [warehouse, lakehouse, iceberg, delta, snowflake, bigquery, kimball, data-vault]
weight: high
audience_levels: [mid, senior, staff]
when_to_ask:
  - "el usuario menciona Snowflake, BigQuery, Redshift, Databricks"
  - "habla de Iceberg, Delta Lake, lakehouse"
  - "describe modelado dimensional (Kimball, Data Vault, OBT)"
---

## Criterios clave

- **Storage tier**: warehouse (Snowflake, BQ, Redshift, ClickHouse) para SQL analítico; lakehouse (Iceberg, Delta, Hudi) sobre object storage para volumen + ML; warehouse-on-lake patterns convergen.
- **Modelado**: Kimball/star schema para reporting clásico. Data Vault para org grandes con muchas fuentes. OBT (One Big Table) para casos simples / dashboards. Medallion (bronze/silver/gold) para lakehouse.
- **Particionado** por tiempo (común) o por tenant (multi-tenant). Reduce scan + permite expirar viejo barato.
- **File format**: Parquet por defecto (columnar, compresión, predicate pushdown). Avro para streaming. JSON solo para landing raw.
- **Schema evolution**: añadir columna OK; renombrar/borrar requiere versionar (esquema Iceberg permite). Documenta cambios con changelog.
- **Type safety**: tipos correctos (no `string` para fechas o números). Decimal con precision para money, no float.
- **Slowly changing dimensions** (SCD): tipo 1 (overwrite), tipo 2 (versionar history), tipo 3 (limited history). Elige por business need.

## Preguntas guía

- "¿Qué warehouse / lakehouse usas? ¿Por qué esa elección?"
- "¿Qué patrón de modelado: Kimball, Data Vault, OBT, medallion?"
- "¿Cómo particionas tus tablas grandes?"
- "Cuéntame de un schema change que tuvo que ser cuidadoso. ¿Cómo lo coordinaste?"
- "¿Manejas SCDs? ¿Qué tipo y por qué?"
- "¿Tienes cost monitoring por query/usuario en el warehouse?"

## Señales de seniority

- **Mid**: tablas estilo OBT, particionado por fecha, schema simple.
- **Senior**: star schema o data vault aplicado bien, particionado + clustering, SCD tipo 2 donde aplica, conoce Iceberg/Delta, cost-aware.
- **Staff/Principal**: gobierna el data model org-wide, define convenciones de naming/types, gestiona migrations grandes (warehouse swap, Kimball→Vault), trabaja con analytics teams en data contracts.

## Anti-patterns

- `SELECT *` en queries que recorren tablas particionadas → ignora pruning.
- Sin partition o cluster keys → full table scans constantes.
- `float` para precios monetarios → errores de redondeo eternos.
- Schema changes sin coordinación → BI dashboards rotos a las 9:00.
- Snapshots overwrite sin history → "qué tenía la tabla la semana pasada" imposible.
- File format JSON en gold layer → scans lentos, sin compresión.
- "Una tabla por modelo de negocio" sin abstracción → mantenimiento explosivo.

## Recursos

- *The Data Warehouse Toolkit* — Kimball (libro de referencia).
- Iceberg / Delta Lake docs (especialmente time travel + schema evolution).
- *Fundamentals of Data Engineering* — Reis & Housley.
- dbt Labs blog (modeling guides).
- Databricks Lakehouse docs.
- Snowflake / BigQuery best-practice guides oficiales.
