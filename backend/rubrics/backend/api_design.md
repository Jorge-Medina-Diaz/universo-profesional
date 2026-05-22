---
sector: backend
slug: backend/api_design
title: "Diseño de APIs (REST, GraphQL, RPC)"
subtitle: "Lo que diferencia un buen diseño de API de uno mediocre"
tags: [api, rest, graphql, contract, idempotency, versioning, pagination]
weight: high
audience_levels: [junior, mid, senior, staff]
when_to_ask:
  - "el usuario menciona endpoints o API"
  - "habla de integración entre servicios"
  - "match a una oferta backend con responsabilidad de API"
---

## Criterios clave

- **Versionado explícito**: path `/v1/` o header `Accept-Version`. Nunca mezclar versiones en el mismo recurso. La política de breaking-change debe estar documentada.
- **Idempotencia** en operaciones mutantes: PUT/DELETE idempotentes por contrato. POST mutante con `Idempotency-Key` header (patrón Stripe) cuando el cliente puede reintentar.
- **Errores estructurados**: `application/problem+json` (RFC 7807) o equivalente. Nunca 200 OK con `{"error": ...}` en el body.
- **Paginación**: cursor-based (opaque tokens) > offset. Offset rompe con writes concurrentes. Devolver `next_cursor` y `has_more`.
- **Rate limiting** documentado: `X-RateLimit-Limit`, `X-RateLimit-Remaining`, `X-RateLimit-Reset`, `Retry-After` en 429.
- **Contratos como código**: OpenAPI/JSON Schema en el repo, versionados, validados en CI. No autogenerar el contrato del runtime — invierte el flujo: contrato → handlers.
- **Cache-Control + ETag** en GETs estables. Conditional requests (`If-None-Match`) bajan carga sin lógica adicional.

## Preguntas guía

- "¿Cómo manejas el versionado del API y las deprecaciones?"
- "¿Tienes idempotency keys en operaciones críticas (pagos, creación de recursos)?"
- "¿Cómo documentas el contrato: OpenAPI, AsyncAPI, GraphQL SDL? ¿Está en el repo o autogenerado?"
- "¿Paginas por cursor o por offset? ¿Cómo lo decides?"
- "Cuéntame de una vez que tuviste que romper compatibilidad — ¿cómo lo comunicaste?"
- "¿Cómo testeas que el contrato no se ha roto? Pact, schema diff, golden tests…?"

## Señales de seniority

- **Junior**: CRUD básico, REST. Conoce los códigos de estado HTTP y JSON. Probablemente no ha tocado paginación cursor.
- **Mid**: paginación, filtros, autenticación (JWT/OAuth), tests de integración. Errores estructurados. Conoce idempotency pero quizás no la aplica sistemáticamente.
- **Senior**: idempotency keys, contract testing, deprecation lifecycle, observabilidad por endpoint (RED metrics), gestión de errores cliente/servidor con problem+json, rate limiting con headers correctos.
- **Staff/Principal**: governance del API estate (RFCs, decision records), breaking-change policy con calendario, federation/composition (GraphQL federation, BFF, gateway), retro-compatibilidad multi-año, contratos como producto.

## Anti-patterns

- "PUT que crea recursos sin ID predecible por el cliente" — debería ser POST con `Location` header.
- Mezclar paginación offset con filtros mutables → resultados duplicados o saltados bajo writes concurrentes.
- 200 OK con `{"error": "..."}` en el body — usa códigos HTTP correctos. Si no, no se puede cachear ni reintentar correctamente.
- Versionar con `?version=N` query param sin path canónico → frena CDN y cache layers.
- "Endpoints sobre verbos": `POST /createUser`, `POST /deleteUser` — colapsa a un solo modelo recurso/verbo.
- Devolver el password hasheado, secrets internos o `created_by_user_email` en respuestas que cualquier cliente puede ver.

## Recursos

- *REST API Design Rulebook* — Mark Massé. Libro corto, denso, sin paja.
- Stripe API docs — la referencia para idempotency keys, versioning con header, pagination cursor.
- GitHub REST API — buen ejemplo de pagination + Link header.
- *Designing Web APIs* — Brenda Jin & co.
- RFC 7807 (Problem Details for HTTP APIs).
- AsyncAPI — equivalente a OpenAPI para event-driven.
