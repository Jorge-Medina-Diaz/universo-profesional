---
sector: frontend
slug: frontend/state_perf
title: "Estado, performance y Core Web Vitals"
subtitle: "Hacer que la app sea rápida sin sobre-optimizar"
tags: [performance, perf-budget, lcp, inp, cls, optimistic-ui, react-query, lighthouse]
weight: high
audience_levels: [junior, mid, senior, staff]
when_to_ask:
  - "el usuario menciona performance, Core Web Vitals, Lighthouse"
  - "habla de state management, optimistic UI, suspense"
  - "describe lag/jank o user-perceived latency"
---

## Criterios clave

- **Performance budget por ruta**: LCP < 2.5s, INP < 200ms, CLS < 0.1. Definido en código (Lighthouse CI) que rompe el build si se excede.
- **Server state ≠ client state**: usar React Query / SWR / TanStack Query para server. Local state (modales abiertos, focus, drafts) con useState/Zustand.
- **Optimistic UI** donde aplica: mutation dispara update inmediato; si falla, rollback con feedback. No para operaciones con riesgo de write-conflict serio.
- **Suspense + transitions**: navegación entre rutas con `useTransition`, fallback estable, no flash.
- **Image optimization**: `<img loading="lazy">`, sizes responsive, AVIF/WebP, dimensiones explícitas para evitar CLS.
- **Code-splitting por ruta** + lazy import para componentes pesados (editores ricos, charts).
- **Web Workers** para lo pesado (parsing, crypto, image processing). El hilo principal está para UI.
- **Profiling con DevTools** + React Profiler. Mide antes de optimizar.

## Preguntas guía

- "¿Mides Core Web Vitals en producción? ¿Cómo (RUM, sintético)?"
- "¿Tienes performance budget? ¿Se enforza en CI?"
- "Cuéntame de una optimización de perf real — ¿cómo la mediste, qué moviste?"
- "¿Cuándo usas optimistic UI? ¿Has tenido casos de rollback complejo?"
- "¿Cómo manejas componentes que renderizan mucho (listas largas, tablas grandes)?"
- "¿Has usado Web Workers? ¿Para qué?"

## Señales de seniority

- **Junior**: Lighthouse local verde → contento. No mide RUM. Quizás un memo aquí y allá sin razón clara.
- **Mid**: React Query/SWR para fetches, `React.memo` consciente, code-splitting por ruta, dimensiones de imagen. Conoce LCP/INP/CLS de oídas.
- **Senior**: budget enforcement en CI, optimistic mutations con rollback, virtualization en listas largas, profiling con DevTools/Profiler, conoce trade-offs de hydration, sabe cuándo `useMemo`/`useCallback` ayuda y cuándo es ruido.
- **Staff/Principal**: define la perf strategy, gestiona el bundle budget total, instrumenta RUM real (Vercel Analytics, SpeedCurve, custom), trabaja con backend para HTTP/2, edge caching, prefetching inteligente. Considera perf parte del producto.

## Anti-patterns

- `useMemo` y `useCallback` en TODO sin medir — añade overhead sin beneficio.
- Bundle gigante porque importas la librería entera (`import _ from 'lodash'` en vez de `lodash-es` con tree-shaking).
- Imagenes sin width/height → CLS catastrófico.
- "Optimistic UI" sin pensar en errores → estado inconsistente sin feedback.
- `setState` en bucles cerrados → renders cascada.
- Polling cada 500ms cuando podías usar SSE o WebSocket.
- Renderizar 10000 filas sin virtualization (react-window, TanStack Virtual).

## Recursos

- web.dev/vitals — la doc oficial de Core Web Vitals.
- Addy Osmani blog y libros (*Image Optimization*, *Learning Patterns*).
- React Query docs (filosofía de server state).
- Vercel Analytics / SpeedCurve para RUM real.
- Chrome DevTools Performance panel (la mejor herramienta a la mano).
- *High Performance Browser Networking* — Ilya Grigorik. Libro denso, fundacional.
