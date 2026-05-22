---
sector: backend
slug: backend/data_layer
title: "Capa de datos: modelado, migrations, transacciones, cache"
subtitle: "Lo que distingue a quien diseña datos de quien escribe SQL ad-hoc"
tags: [database, postgres, modeling, migrations, transactions, cache, search]
weight: high
audience_levels: [junior, mid, senior, staff]
when_to_ask:
  - "el usuario menciona Postgres, MySQL, MongoDB u otra DB"
  - "habla de modelado de datos, esquema o schema design"
  - "habla de migraciones, rendimiento de queries o cache"
---

## Criterios clave

- **Modelado primero**: normaliza hasta 3NF salvo razón explícita para denormalizar. Decisiones de denormalización deben ser conscientes (rendimiento, simplicidad de query) y reversibles.
- **Migrations seguras**: cada migration es **online** (sin bloquear writes), idempotente, con `down` plausible. Patrón expand/contract para columnas: nullable nuevo → backfill → not-null → drop viejo en migration posterior.
- **Transacciones**: SERIALIZABLE solo cuando hace falta. Aislar el "unit of work" en el repositorio/use-case, no en el handler. `SELECT FOR UPDATE` o advisory locks para flujos con contención.
- **Indexing**: índice antes de optimizar query. Compuestos en orden de selectividad. Conoce `EXPLAIN ANALYZE` y `pg_stat_statements`. Sin índices "por si acaso" — cuestan en writes y mantenimiento.
- **Cache invalidation explícita**: TTL + invalidación basada en eventos. Anti: cache "que se refresca solo". Patrón cache-aside con `set_if_changed`.
- **Búsqueda**: `tsvector` + GIN para texto. pgvector + HNSW para embeddings. Elasticsearch/Meilisearch solo si hay reason real (multilingüe, scoring complejo, facetas).

## Preguntas guía

- "¿Cómo gestionas las migrations? ¿Tienes política de zero-downtime?"
- "Cuéntame de un índice que añadiste tras encontrar un problema de rendimiento."
- "¿Qué nivel de aislamiento usas por defecto? ¿Has tenido que cambiarlo alguna vez?"
- "¿Cómo invalidas tus caches? ¿Tienes problemas de coherencia entre cache y BD?"
- "¿Has usado pgvector o búsqueda full-text? ¿Cómo lo evaluaste?"
- "¿Cómo monitorizas queries lentas en producción?"

## Señales de seniority

- **Junior**: SQL básico, JOINs, conoce índices conceptualmente. Quizás no ha tocado migrations en prod.
- **Mid**: diseña esquemas razonables, escribe migrations forwards-compatible, conoce transactions y aislamiento por encima. Sabe leer EXPLAIN.
- **Senior**: piensa en expand/contract antes de tocar nada en prod, observa `pg_stat_statements`, conoce trade-offs de denormalización, usa cache-aside con invalidación explícita, ha rescatado una DB de un long-running query.
- **Staff/Principal**: governance del esquema (shared ownership, RFC para cambios grandes), gestión de hot tables (partitioning, sharding, read replicas), políticas de retention/archive, capacity planning, runbooks para incident response.

## Anti-patterns

- `ALTER TABLE ... ADD COLUMN ... NOT NULL DEFAULT 'x'` en tabla grande sin `SET DEFAULT ... ; SET NOT NULL` por separado → table rewrite + lock catastrófico.
- Borrar columnas en la misma deploy en que se elimina el código que las usa → rollback imposible.
- "ORM se encarga del cache" — el ORM no invalida cache externo, y su cache de identidad ensucia cuando hay writes concurrentes.
- N+1 queries no detectados (lazy loading dentro de loops).
- Usar UUID v4 como PK sin entender el coste de fragmentación de índices clustered (en MySQL InnoDB es severo).
- Tests que no resetean transacciones entre cases → contaminación cruzada.

## Recursos

- *Designing Data-Intensive Applications* — Martin Kleppmann (referencia obligada).
- Postgres docs sobre `EXPLAIN`, `pg_stat_statements`, locks.
- *Database Internals* — Alex Petrov.
- Brandur Leach blog (Postgres + product engineering).
- *The Art of PostgreSQL* — Dimitri Fontaine.
