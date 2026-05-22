---
sector: mobile
slug: mobile/architecture
title: "Arquitectura mobile (iOS, Android, cross-platform)"
subtitle: "Cómo se estructura una app para sobrevivir el ciclo de vida"
tags: [ios, android, swift, kotlin, react-native, flutter, mvvm, mvi, navigation]
weight: high
audience_levels: [junior, mid, senior, staff]
when_to_ask:
  - "el usuario menciona iOS, Android, Swift, Kotlin, React Native, Flutter"
  - "habla de arquitectura mobile (MVVM, MVI, TCA, Clean)"
  - "describe gestión de estado, navegación o DI en mobile"
---

## Criterios clave

- **State management con patrón claro**: MVVM (clásico), MVI (unidirectional), TCA (Composable), Redux-like. Lo importante es **un solo modelo** en el equipo, no mezcla.
- **Navigation declarativa**: SwiftUI NavigationStack, Jetpack Navigation, Expo Router, React Navigation. Stack + tabs + modals como tipos primitivos.
- **Dependency injection** explícita (Koin, Hilt, Swift DI manual, RN context). Singleton global es deuda.
- **Offline-first** donde aplica: local-first (SQLite/Realm/CoreData) + sync layer. La red es un detalle, no la fuente de verdad.
- **Lifecycle aware**: cancelar fetches en `onDestroy`/`unmount`, no leak observers. Coroutines/Combine/RxJava con scope correcto.
- **Capa de networking** centralizada: un cliente HTTP, retry/backoff, auth interceptor, error mapping a domain errors.
- **Feature flags + remote config**: cambios sin update store. Firebase Remote Config, LaunchDarkly, ConfigCat.

## Preguntas guía

- "¿Qué patrón de arquitectura usas (MVVM, MVI, TCA)? ¿Por qué?"
- "¿Cómo manejas navegación — declarativa, imperativa?"
- "Cuéntame de tu networking layer — ¿cliente único, error handling?"
- "¿Tienes funcionalidad offline? ¿Cómo modelaste la sincronización?"
- "¿Cómo gestionas los estados de lifecycle? ¿Coroutines/Combine/Rx?"
- "¿Has migrado de un framework a otro alguna vez (UIKit→SwiftUI, View→Compose)?"

## Señales de seniority

- **Junior**: UI básica, llamadas API en ViewController/Activity, estado en variables locales.
- **Mid**: MVVM, navigation centralizada, networking client con retry, conoce Coroutines/Combine.
- **Senior**: arquitectura limpia (domain/data/presentation), DI explícita, offline-first donde aplica, testing de ViewModels/UseCases, feature flags.
- **Staff/Principal**: define la arquitectura de la app (o multi-app suite), gobierna la migración tech-debt (UIKit→SwiftUI grad), trabaja con backend en API design, mide app-level metrics (startup, crash-free rate, ANR).

## Anti-patterns

- Lógica de negocio en ViewController/Activity → imposible de testear.
- "Singleton manager" global para todo (NetworkManager, UserManager) sin DI.
- `runBlocking` / `Task { ... }` sin scope → leaks y crashes.
- Navigation con strings hard-coded sin tipo.
- Mezclar RxJava + Coroutines + LiveData en mismo módulo.
- "Refresh manual" en cada pantalla en lugar de un patrón observable centralizado.
- Crashes en lifecycle (acceder a UI tras detach) ignorados como "raros".

## Recursos

- *iOS App Architecture* (objc.io book) o *Modern Concurrency in Swift* (objc.io).
- *Programming Android* — antiguo pero fundacional.
- Pointfree TCA docs (composable patterns).
- Jetpack Compose Mental Model docs.
- React Native New Architecture docs (Fabric, TurboModules).
- *App Architecture in Compose* — Donn Felker.
