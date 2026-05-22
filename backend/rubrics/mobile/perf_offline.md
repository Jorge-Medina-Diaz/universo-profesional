---
sector: mobile
slug: mobile/perf_offline
title: "Performance, offline y experiencia móvil"
subtitle: "Lo que diferencia una app rápida y robusta de una mediocre"
tags: [performance, startup-time, jank, offline, sqlite, realm, image-pipeline]
weight: high
audience_levels: [mid, senior, staff]
when_to_ask:
  - "el usuario menciona performance, startup, jank, frame drops"
  - "habla de offline, sincronización, conflict resolution"
  - "describe image loading, caching, local storage"
---

## Criterios clave

- **Cold start budget**: iOS < 400ms a primer frame interactivo; Android < 1s. Mide con tools nativas (Instruments, Macrobenchmark).
- **60 fps mínimo** (preferible 120fps en devices que lo soportan). Jank visible = bug. Profiling con Tracy/Frame Pacing.
- **Offline-first si la categoría lo pide** (notes, fitness, content): local DB es source of truth, sync en background. Conflict resolution explícita (last-write-wins, CRDT, manual merge).
- **Image pipeline**: thumbnails generados server-side; en cliente, lazy + cache disk LRU (Coil, Glide, SDWebImage, Kingfisher). Nunca descargar full-res si no se muestra.
- **Networking inteligente**: batching, dedup de requests idénticos, prefetch en idle. Reintento exponencial con jitter.
- **Storage**: SQLite con FTS5 para search, Realm/CoreData/Room según platform, SwiftData (iOS 17+). Migrations versionadas con tests.
- **Battery awareness**: workmanager/BGTask con criterios (idle, charging, wifi). No polling de fondo agresivo.
- **Sensores y permisos** justos: solicita lo que usas, cuando lo usas. Permission rationale claro.

## Preguntas guía

- "¿Mides cold start time? ¿Cuál es el budget actual?"
- "¿Tu app es offline-first? Si sí, ¿cómo modelaste la sincronización?"
- "Cuéntame del image pipeline — ¿cache local, server thumbnails?"
- "¿Has tenido issues de batería? ¿Cómo los detectaste y resolviste?"
- "¿Cómo testeas que las migraciones de DB local no rompen datos del usuario?"
- "¿Qué framework de background work usas? ¿Cómo decides qué corre cuándo?"

## Señales de seniority

- **Mid**: Coil/Glide/SDWebImage configurado, SQLite básico, conoce Coroutines/Combine con cuidado de scope.
- **Senior**: cold start budget medido, offline-first con sync explícita, conflict resolution implementada, image pipeline con thumbnails server, battery aware.
- **Staff/Principal**: define la perf strategy de la app, instrumenta tracing custom (start-up trace, scroll perf), trabaja con backend en BFF para mobile (response shape mínima), mide DAU↔perf correlations.

## Anti-patterns

- Cargar full-res images sin thumbnail server.
- "Sync = pull all data on launch" → app inutilizable en redes lentas.
- Background sync que ignora battery / wifi → quejas de los users en reviews.
- Migrations de DB sin tests forwards-compatibility → pérdida de datos en updates.
- Polling cada 5s para detectar cambios → battery drain.
- Permisos pedidos al onboarding sin contexto (location, camera, contacts).
- "Render all" listas de 1000 items sin virtualization (LazyColumn/LazyVStack/FlatList).

## Recursos

- Apple WWDC sessions (Instruments, Performance, App Startup).
- Android Macrobenchmark + Baseline Profiles docs.
- *Designing Mobile Apps* (older but solid).
- Coil/Glide/SDWebImage docs (image strategies).
- Realm/Room migration patterns.
- *Offline-First Mobile Apps* (varios artículos en martinfowler.com).
