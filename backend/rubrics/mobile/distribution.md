---
sector: mobile
slug: mobile/distribution
title: "Distribución: App Store, Play Store, rollouts, crashes"
subtitle: "La parte que no es código pero hace el producto"
tags: [app-store, play-store, testflight, staged-rollout, crashlytics, sentry]
weight: high
audience_levels: [junior, mid, senior, staff]
when_to_ask:
  - "el usuario menciona App Store, Google Play, distribución"
  - "habla de TestFlight, beta tracks, staged rollout"
  - "describe crash reporting, ANR, release management"
---

## Criterios clave

- **Beta channels**: TestFlight (iOS) e Internal/Closed/Open Testing (Android) como pre-prod estándar. Beta amplia 1-2 semanas antes de release general en cambios grandes.
- **Staged rollout**: 1% → 10% → 50% → 100% en Android (nativo). iOS no tiene staged rollout granular hasta 2023 (Phased Release sí: 7 días).
- **Crash reporting** obligatorio: Crashlytics, Sentry, Bugsnag. Filtrar por release + by-user impact. Métricas clave: crash-free users %, crash-free sessions %, ANR rate.
- **Compliance**: App Store guidelines + Google Play policies cambian. Revisar checklist por release. Atributos críticos: privacy (App Privacy Manifest iOS, Data Safety Android), permission rationales.
- **CI/CD para mobile**: Fastlane (o equivalente) para automatizar signing, screenshots, upload. Match para certs iOS.
- **Versioning semántico**: marketing version (1.4.0) + build number autoincremental. Cambios de schema → bump major.
- **Release notes** decentes en cada release. Internos para soporte + externos para users.
- **Hotfix path** definido: cómo se sube un fix urgente cuando hay un crash masivo (expedited review request en iOS, hotfix track en Android).

## Preguntas guía

- "¿Tenéis programa de beta? ¿Cuántos beta testers?"
- "¿Hacéis staged rollout en Android? ¿En iOS Phased Release?"
- "¿Crash reporting con qué tool? ¿Métrica clave que vigiláis?"
- "Cuéntame del último rejection de App Store — cómo lo resolvisteis."
- "¿Cómo gestionáis los certificados/signing en CI?"
- "¿Hotfix path documentado? ¿Tiempo desde detección hasta release?"

## Señales de seniority

- **Junior**: sube builds desde Xcode/AS manualmente. Conoce TestFlight de oídas.
- **Mid**: Fastlane básico, TestFlight + Play Internal Testing usados, Crashlytics integrado.
- **Senior**: staged rollouts disciplinados, crash budget como SLO, App Store guidelines bien conocidas, expedited review path probado, beta program activo con feedback loop.
- **Staff/Principal**: gobierna la release strategy multi-app, mide app-level KPIs (DAU, retention, crash impact en revenue), trabaja con product/legal en privacy compliance, multi-store presence (Amazon, Galaxy, F-Droid).

## Anti-patterns

- Subir builds manualmente desde laptop con certs locales.
- Sin staged rollout → bug afecta 100% antes de detectar.
- Ignorar crashlytics ("ya está reportado, no urgente") hasta que sale en reviews.
- Forzar update agresivo a usuarios sin necesidad real (in-app update prompts cada semana).
- Versionar releases con "1.0", "1.1", "1.1.1" sin bump consistente.
- Privacy labels desactualizadas vs la realidad → rejection o multa.

## Recursos

- App Store Review Guidelines (oficial, leer entera 1 vez).
- Google Play Developer Policy Center.
- Fastlane docs (especialmente "match" para certs).
- *iOS App Distribution & Best Practices* (Apple Developer videos WWDC).
- Bryan Irace + Mobile Native Foundation podcasts.
- App Store Connect API docs (automatización).
