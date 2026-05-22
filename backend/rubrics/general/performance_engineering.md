---
sector: general
slug: general/performance_engineering
title: "Performance engineering: profiling, optimization, caching, load testing"
subtitle: "El arte de saber dónde mirar antes de optimizar"
tags: [performance, profiling, optimization, caching, load-testing, capacity-planning]
weight: medium
audience_levels: [mid, senior, staff]
when_to_ask:
  - "el usuario menciona profiling, optimización, p99, caching"
  - "habla de capacity planning, load testing, k6, JMeter, Gatling"
  - "describe un problema de performance que resolvió"
---

## Criterios clave

- **Profile primero, optimiza después**: no asumir el bottleneck. Tooling: py-spy / async-profiler / pprof / Flame Graphs / Datadog APM / Sentry profiling.
- **Workflow top-down**: medir el end-to-end (p99 desde el cliente), luego ir bajando hasta CPU instruction / DB query lenta. NO empezar por "voy a optimizar este método".
- **Database performance**: EXPLAIN ANALYZE es la primera herramienta. Índices correctos (composite + partial cuando aplica). N+1 detectado con APM. Read replicas para reads. Connection pooling correcto.
- **Caching layers conscientes**: L1 in-process (LRU bounded), L2 Redis/Memcached con TTL + invalidación clara, HTTP caching (Cache-Control + ETag), CDN para assets estáticos.
- **Load testing antes de prod**: k6 / Gatling / Locust con escenarios realistas (no solo "1000 reqs igual"). Soak tests para detectar memory leaks. Stress tests para conocer el breakpoint.
- **Capacity planning**: cuántos reqs/s aguanta una instancia? Cuándo escalo horizontal? Costes asociados. Auto-scaling con métricas custom (no solo CPU).
- **Latencia presupuesto**: cada feature tiene presupuesto p99 + p50 explícito. Si excedes, optimiza o di no.

## Preguntas guía

- "¿Cuándo fue tu último profiling real? ¿Con qué herramienta?"
- "Cuéntame de una optimización que redujo p99 significativamente — cómo encontraste el bottleneck."
- "¿Tienes presupuesto de latencia por endpoint? ¿Lo enforcás?"
- "¿Has hecho load testing antes de un launch grande? Cuéntame del escenario."
- "¿Cuáles son tus 2 capas de caching y por qué esas?"
- "Cuándo fue el último N+1 que pillaste y cómo?"

## Señales de seniority

- **Mid**: optimiza con intuición + Stack Overflow. Sabe qué es un N+1 cuando se lo señalan.
- **Senior**: profile con tooling correcto antes de tocar código. Establece presupuestos de latencia. Caching consciente (no over-caching). Load testing pre-prod.
- **Staff/Principal**: gobierna la cultura de performance en el equipo. Establece SLOs vinculados a perf. Detecta regresiones via CI perf tests. Lleva capacity planning con costes alineados a producto.

## Anti-patterns

- "Es lento" sin medir nada → optimización a ciegas que no mueve la aguja.
- Cachear sin pensar invalidación → bugs sutiles que tardan semanas en aparecer.
- Cachear todo en in-process sin bounds → OOM kills aleatorios.
- Load test que solo hace happy path con 1 query → no representa la realidad.
- Optimizar antes de tener métricas → premature optimization.
- "Multi-region porque a veces es lento" sin entender por qué.

## Recursos

- "Systems Performance" — Brendan Gregg (la biblia).
- Flame Graphs por Brendan Gregg (técnica + tooling).
- "High Performance Browser Networking" — Ilya Grigorik (frontend perf).
- k6 docs + grafana.com/blog (load testing).
- Use The Index Luke (database indexing).
- Discord Engineering blog (lots of perf war stories).
