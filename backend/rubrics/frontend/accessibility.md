---
sector: frontend
slug: frontend/accessibility
title: "Accesibilidad (WCAG, ARIA, navegación)"
subtitle: "Lo que separa interfaces inclusivas de interfaces 'que se ven bien'"
tags: [a11y, wcag, aria, screen-reader, keyboard, focus, contrast]
weight: high
audience_levels: [junior, mid, senior, staff]
when_to_ask:
  - "el usuario menciona accesibilidad, a11y, WCAG, ARIA"
  - "describe componentes UI custom (modales, dropdowns, tabs)"
  - "trabaja en producto público / B2C donde inclusión es ROI"
---

## Criterios clave

- **WCAG 2.1 AA como mínimo**, AAA donde se pueda sin sacrificar diseño. Las 4 categorías: perceivable, operable, understandable, robust.
- **HTML semántico primero**, ARIA después. Un `<button>` real le gana a un `<div role="button">` con todos los handlers del mundo.
- **Focus management**: orden lógico (`tabindex` no negativo salvo skip-link), `:focus-visible` siempre. Modal abre → trap focus dentro; cierra → devuelve a quien lo abrió.
- **Keyboard equivalence**: todo lo que se hace con mouse se puede con teclado. Hover-only menus = barrera.
- **Screen reader testing real**: VoiceOver (macOS/iOS), NVDA (Windows), TalkBack (Android). No basta con axe-core automatizado.
- **Contraste**: texto 4.5:1, large text 3:1, UI 3:1. Verificar con tools tipo WebAIM Contrast Checker. Cuidado con texto sobre fondos amarillos/cyan tipo "sunbeam".
- **Live regions** (`aria-live`) para cambios dinámicos: toasts, validation errors, loading states. Sin abusar (no anunciar cada keystroke).
- **Form labels asociados** (`<label for>` o anidados). Errors enlazados con `aria-describedby`. `required` semántico + comunicado al SR.

## Preguntas guía

- "¿Cómo testeas accesibilidad? ¿Automatizado, manual, ambos?"
- "Cuéntame del último modal complejo que hiciste — ¿cómo manejaste focus?"
- "¿Tienes auditorías formales con un SR (VoiceOver/NVDA)? ¿Frecuencia?"
- "¿Cómo decides cuándo usar ARIA y cuándo HTML semántico?"
- "¿Has tenido feedback real de usuarios con discapacidad? ¿Qué aprendiste?"
- "¿Qué KPIs usas para a11y? Lighthouse, axe, Wave, manual…?"

## Señales de seniority

- **Junior**: sabe que `alt` en imágenes existe. Lighthouse a11y verde y listo.
- **Mid**: HTML semántico consistente, contraste OK, labels en forms, conoce `aria-label` y `aria-describedby`.
- **Senior**: focus trap en modales, keyboard navigation completa, live regions, screen reader testing manual, define el a11y baseline del equipo (lint rules + manual checklist).
- **Staff/Principal**: lidera auditorías formales, trabaja con usuarios reales (advisory board), embebe a11y en design tokens (focus rings, contrast), define los hand-off Figma↔code con anotaciones a11y, mide impacto en métricas de negocio.

## Anti-patterns

- `<div onClick>` para acciones — no es tabable, no anuncia rol, no responde a Enter.
- Modal sin focus trap → usuario tabea al fondo del DOM.
- Color como único transmisor de información ("verde = ok, rojo = error") sin texto o icono.
- `placeholder` como sustituto de `<label>` — desaparece al escribir.
- Animaciones largas sin `prefers-reduced-motion`.
- "Skip to content" link sin estilo (invisible) o con estilo permanente (interfiere).
- Tooltips con info crítica que solo aparece on-hover.

## Recursos

- WCAG 2.1 quick reference (W3C oficial).
- *Inclusive Components* — Heydon Pickering (libro gratis online, oro puro).
- Sara Soueidan blog (accessibility patterns).
- WebAIM (recursos + contrast checker + survey anual de SR users).
- Adrian Roselli blog (componentes a11y en profundidad).
- Storybook a11y addon + axe-core para CI.
- Deque University (cursos).
