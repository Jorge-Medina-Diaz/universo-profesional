---
sector: backend
slug: backend/distributed_systems
title: "Distributed systems: discovery, mesh, circuit breakers, tracing"
subtitle: "Lo que diferencia un microservicios real de un monolito mal dividido"
tags: [distributed, microservices, service-mesh, circuit-breaker, tracing, gRPC]
weight: high
audience_levels: [senior, staff, principal]
when_to_ask:
  - "el usuario menciona microservicios, service mesh, gRPC, circuit breakers"
  - "habla de distributed tracing, retries, bulkheads, deadlines"
  - "describe sistemas con 10+ servicios coordinándose"
---

## Criterios clave

- **Service discovery + load balancing**: DNS-based + health checks + outlier detection. Client-side LB (Envoy, gRPC) cuando hay sidecars. Service mesh (Istio, Linkerd) si el volumen lo justifica.
- **Resiliencia patterns**: circuit breakers (Hystrix-style, ahora resilience4j / Polly), bulkheads (separar pool por dependencia), timeouts cascading correctos, retries con jittered backoff + idempotency.
- **Distributed tracing**: W3C trace context propagado en TODO el código (HTTP + gRPC + Kafka). OpenTelemetry como estándar. Sampling adaptativo (head + tail).
- **Deadlines/budgets**: cada request lleva deadline propagado downstream (no timeouts independientes que se acumulan a 30s).
- **Coreografía vs orquestación**: claro cuándo events (coreo) y cuándo workflows (orquestación tipo Temporal/Cadence).
- **gRPC bien usado**: proto contracts versionados, server reflection en dev, gRPC-web/Connect para browser cuando aplica.
- **Failure injection en prod**: chaos eng integrado al CI/CD o GameDays. Sin "no se ha caído nunca" → significa "no lo hemos testado nunca".

## Preguntas guía

- "¿Cuántos servicios tienes en prod? ¿Cuál es el ratio reqs sincronos vs async?"
- "¿Service mesh — sí, no, por qué? Trade-offs reales en tu caso."
- "¿Cómo manejas retries entre servicios? ¿Idempotency en endpoints?"
- "Cuéntame del último cascading failure que tuvisteis."
- "¿Distributed tracing — con qué herramienta y cuánta cobertura real?"

## Señales de seniority

- **Mid**: monolito o pocos servicios, REST entre ellos, tracing con logs correlados.
- **Senior**: 10+ servicios, gRPC + REST, retries + circuit breakers explícitos, OpenTelemetry, sabe cuándo NO usar mesh.
- **Staff/Principal**: arquitecturas con 50+ servicios o múltiples regiones, mesh policy decisions, deadline propagation enforced, multi-tenancy + bulkhead patterns, postmortems de cascading failures con root cause sistémico.

## Anti-patterns

- "Microservicios" sin async communication → distributed monolith (peor que monolito).
- Retries sin idempotency → corrupción silenciosa.
- Timeouts independientes que suman 30s+ end-to-end → user ya cerró el browser.
- Logs sin correlation_id / trace_id → debugging imposible.
- Service mesh "porque mola" → 10x complejidad para 10 microservicios.
- Mismo pool de threads/conexiones para todo → 1 dependencia lenta tumba el servicio.

## Recursos

- "Designing Data-Intensive Applications" — Martin Kleppmann (referencia).
- "Building Microservices" — Sam Newman.
- "Release It!" — Michael Nygard (stability patterns).
- OpenTelemetry docs + Cloud Native Computing Foundation papers.
- Temporal.io blog / Cadence docs (orchestration).
- Charity Majors blogs en honeycomb.io.
