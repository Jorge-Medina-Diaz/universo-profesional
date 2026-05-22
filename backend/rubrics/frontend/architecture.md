---
sector: frontend
slug: frontend/architecture
title: "Arquitectura frontend: rendering, routing, state, splitting"
subtitle: "Cuándo SPA, cuándo SSR, cuándo RSC, y por qué"
tags: [react, vue, svelte, next, remix, ssr, ssg, rsc, routing, code-splitting]
weight: high
audience_levels: [junior, mid, senior, staff]
when_to_ask:
  - "el usuario menciona React, Vue, Svelte, Next, Remix, Astro"
  - "habla de SSR/SSG/RSC, hidratación, FOUC"
  - "describe arquitectura de una webapp grande"
---

## Criterios clave

- **Elegir rendering por feature**, no por proyecto. Landing pública → SSG/pre-render. Dashboard auth-gated → SPA. Detalle de producto con SEO + interactividad → SSR/RSC.
- **Routing como árbol de capas**: file-system routing (Next, Remix, TanStack Router) sobre el manual cuando hay > 10 rutas. Layouts compartidos a nivel de árbol.
- **State**: distinguir **server state** (cache de fetches → React Query, SWR) de **client state** (UI local → useState, Zustand). Mezclarlos es la causa #1 de bugs.
- **Code-splitting por ruta** automático. Lazy-load para modales y views grandes. `Suspense` con fallback decente.
- **Data fetching colocated con la ruta** (loaders en Remix/TanStack, `getServerSideProps` en Next, RSC). Evitar useEffect para fetch primario.
- **Diseño primero**: design tokens en CSS vars o JS, theme switching como dato, NO duplicar valores entre Figma y código.
- **Forms**: validación con Zod/Valibot, client + server. Field-level errors + form-level. `react-hook-form` o `Formik` para forms complejos.

## Preguntas guía

- "¿Cómo decides cuándo SSR vs SPA vs SSG en una nueva feature?"
- "¿Tienes separados server state y client state? ¿Qué libs usas?"
- "Cuéntame de la estrategia de code-splitting — ¿lazy por ruta, por modal?"
- "¿Cómo manejas los formularios complejos? ¿Validación cliente y servidor?"
- "¿Cómo organizas los design tokens entre Figma y código?"
- "¿Has migrado entre frameworks/versions grandes alguna vez? Cómo lo planteaste?"

## Señales de seniority

- **Junior**: SPA con React, useState, fetch directo en useEffect. JSX cómodo, no sabe RSC vs CSR vs SSR.
- **Mid**: React Query / SWR para fetches, code-splitting por ruta, rutas con layouts, conoce SSR conceptualmente.
- **Senior**: elige rendering por feature, tiene strategy de forms con validación dual, design tokens vivos, optimistic UI cuando aplica, conoce trade-offs de RSC.
- **Staff/Principal**: gobierna la arquitectura frontend de la org, define el meta-framework (Next vs Remix vs custom), planifica migraciones graduales, propulsa convenciones (folder structure, naming, imports), trabaja con design system team.

## Anti-patterns

- `useEffect(() => { fetch(...) }, [])` en cada componente sin cache de server state.
- "Todo Redux" — Redux para state local UI es over-engineering desde 2020.
- Form sin validación servidor — el cliente miente siempre.
- "Lazy-load" envolviendo un bundle de 800KB con un Suspense fallback de 5ms.
- Mezclar SSR y CSR del mismo dato sin reconciliación → bugs de hidratación silenciosos.
- Reinventar routing en lugar de usar el del framework.
- Importar todos los iconos de una librería en bundle inicial (lucide-react, react-icons sin tree-shaking).

## Recursos

- patterns.dev — patrones frontend modernos.
- *Frontend Architecture for Design Systems* — Micah Godbolt.
- React docs (la nueva docs.react.dev es excelente, especialmente "Thinking in React").
- Remix philosophy docs (web fundamentals first).
- Theo / t3.gg — opiniones modernas (con sus matices).
- Josh Comeau blog — frontend en profundidad.
