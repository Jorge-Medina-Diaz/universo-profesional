---
sector: backend
slug: backend/event_driven_architecture
title: "Event-driven architecture: sourcing, CQRS, sagas, idempotency"
subtitle: "Cuándo los eventos son la columna vertebral y no un complemento al CRUD"
tags: [event-driven, event-sourcing, cqrs, saga, idempotency, eventual-consistency]
weight: medium
audience_levels: [senior, staff]
when_to_ask:
  - "el usuario menciona eventos, event sourcing, CQRS, sagas"
  - "habla de eventual consistency, choreography, orchestration"
  - "describe sistemas con Kafka/Pulsar como espinazo (no solo logs)"
---

## Criterios clave

- **Eventos como verdad**: en event-sourced systems, la tabla `events` es la fuente; el state actual es un derived view (read model). Append-only, immutable, versionable.
- **CQRS bien aplicado**: separar write model (comando → genera eventos) del read model (queries optimizadas). NO aplicar CQRS si el sistema es CRUD simple — over-engineering.
- **Idempotency en producers + consumers**: dedup por event_id + sequence_number. Outbox pattern para garantizar at-least-once delivery sin perder writes a DB.
- **Sagas para transacciones distribuidas**: orchestrator-based (control central, más simple de debug) vs choreography-based (cada servicio reacciona a eventos, menos acoplamiento, más opaco). Compensating actions explícitas.
- **Event schema management**: contracts versionados (Avro / Protobuf / JSON Schema). Compatibility rules (backward / forward / full). Schema registry (Confluent / Apicurio).
- **Replay capacity**: pueden los read models reconstruirse 100% desde el event log? Si no, no es event-sourced de verdad.
- **Observability events-aware**: traces que cruzan async boundaries (W3C trace context propagation). Dashboards por event type.

## Preguntas guía

- "¿Tu sistema es event-sourced o solo usa colas para async tasks?"
- "¿CQRS aporta complejidad justificada en tu caso? ¿O fue cargo cult?"
- "¿Cómo manejas idempotency en consumers? ¿Outbox pattern?"
- "¿Sagas — orchestration o choreography? ¿Compensating actions probadas?"
- "¿Tienes schema registry? ¿Cómo gestionas breaking changes?"
- "¿Has tenido que replay el event log en producción? ¿Cuánto tardó?"

## Señales de seniority

- **Mid**: usa colas para async (Kafka como log), entiende producer/consumer, sabe partition keys importan.
- **Senior**: implementa event sourcing acotado a un bounded context, sagas con outbox, schema versioning explícito, idempotency consumers.
- **Staff/Principal**: gobierna estrategia event-driven a nivel arquitectura, balanza CQRS vs CRUD según caso, lleva schema governance (compatibility, deprecation), eventual consistency conversaciones con producto.

## Anti-patterns

- "Event sourcing" sin replay testado = ilusión.
- CQRS en todo el sistema "porque está de moda" — complejidad sin pago.
- Sagas sin compensating actions → estados inconsistentes silenciosos.
- Eventos sin schema versioning → un breaking change tumba todos los consumers.
- Outbox sin retry policy → losses cuando el broker se cae.
- Mezclar partition key con business id sin pensar (no se puede particionar después sin migration costosa).

## Recursos

- "Designing Event-Driven Systems" — Ben Stopford (libro corto, denso, gratis).
- "Patterns of Enterprise Application Architecture" — Martin Fowler.
- Eventide Project (Ruby event sourcing).
- Confluent blog (Kafka best practices).
- Debezium docs para CDC + outbox.
