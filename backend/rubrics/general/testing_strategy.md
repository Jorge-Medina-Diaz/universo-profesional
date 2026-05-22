---
sector: general
slug: general/testing_strategy
title: "Testing strategy: pyramid, contract testing, mutation, chaos"
subtitle: "Lo que distingue 'tenemos tests' de 'tenemos confianza para hacer deploy a las 17h'"
tags: [testing, pyramid, contract-testing, mutation-testing, chaos, integration, e2e]
weight: medium
audience_levels: [mid, senior, staff]
when_to_ask:
  - "el usuario menciona test pyramid, contract testing, Pact"
  - "habla de mutation testing, Stryker, chaos engineering"
  - "describe cómo gana confianza para deploys"
---

## Criterios clave

- **Pyramid honesta**: muchos unit tests (rápidos, mocks de I/O), pocos integration (DB real, queues), poquísimos E2E (UI happy paths). Ratio aproximado 70/25/5.
- **Contract testing**: Pact / Spring Cloud Contract entre servicios para evitar el "consumer-provider drift" sin pagar el coste de E2E completos.
- **Mutation testing**: Stryker / Pitest. Detecta tests que pasan pero no detectarían bugs reales. Aplicar en módulos críticos (billing, auth).
- **Test data**: factories (factory_boy / FactoryBot) > fixtures rígidas. Bases de datos con migrations testadas (no solo el schema final).
- **CI fast feedback**: unit < 5min, integration < 15min, E2E < 30min. Si no, falla por timeout y nadie lo arregla.
- **Coverage como señal, no como meta**: 80% coverage que testea getters es peor que 50% en lógica de negocio. Branch coverage > line coverage.
- **Chaos / failure injection**: GameDays o automated chaos en pre-prod. "No se ha caído" significa "no lo hemos testado, no que sea robusto".

## Preguntas guía

- "¿Cuál es tu pyramid real (no la ideal)?"
- "¿Tienes contract testing entre servicios? ¿Qué prevendrá un breaking change?"
- "¿Has hecho mutation testing? ¿Qué tests tiraste tras ver los resultados?"
- "¿Cuánto tarda tu CI para PR de developer? ¿Y para release?"
- "Cuéntame del último flaky test que tuviste y cómo lo resolviste."

## Señales de seniority

- **Mid**: unit tests, alguna integration, evita los mocks excesivos.
- **Senior**: pyramid clara con ratios pensados, contract testing donde tiene sentido, factories para test data, CI rápido, chaos engineering empezando.
- **Staff/Principal**: gobierna estrategia de testing org-wide, mutation testing en módulos críticos, balance entre coverage y velocity, education sobre testing en equipos junior.

## Anti-patterns

- "Tenemos 90% coverage" sin medir branch coverage → métrica vanity.
- Pyramid invertida (más E2E que unit) → CI de 2h, flakiness constante, deploys con miedo.
- Mocks excesivos → tests pasan, prod rompe.
- Snapshot tests sin revisar el snapshot → "se aprueba el bug automáticamente".
- Sin factories → fixtures rígidas que se rompen en cada cambio de schema.
- Tests "deterministicos" que dependen de `time.now()` sin freeze.

## Recursos

- "Working Effectively with Legacy Code" — Michael Feathers (testing seam patterns).
- "The Art of Unit Testing" — Roy Osherove.
- Martin Fowler's "Test Pyramid" article + actualizaciones.
- Pact docs + casos reales de microservicios.
- Stryker (JS/Python/.NET) docs.
- Kent C. Dodds "Testing Trophy" (variante moderna de pyramid).
