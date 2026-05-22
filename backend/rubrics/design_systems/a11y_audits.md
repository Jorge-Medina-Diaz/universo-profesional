---
sector: design_systems
slug: design_systems/a11y_audits
title: "Auditorías a11y: componentes, automated + manual"
subtitle: "Cómo un design system enforza accesibilidad por defecto"
tags: [a11y, audit, axe, lighthouse, storybook, manual-testing, screen-reader]
weight: high
audience_levels: [mid, senior, staff]
when_to_ask:
  - "el usuario menciona auditoría de accesibilidad, axe, WCAG"
  - "habla de testing manual con screen reader"
  - "describe componentes design system con a11y built-in"
---

## Criterios clave

- **A11y como criterio de aceptación**: ningún componente publica sin checklist a11y. Es DoD (definition of done), no opcional.
- **Automatización en CI**: axe-core via @axe-core/playwright o jest-axe. Falla build cuando hay críticos.
- **Storybook + a11y addon**: cada story pasa axe. Stories cubren estados (default, hover, focus, disabled, error).
- **Tests manuales por componente**: keyboard nav, screen reader (VoiceOver mac/iOS, NVDA Win, TalkBack Android). Documenta el comportamiento esperado.
- **Componentes "headless" si son complejos**: Radix, Headless UI, React Aria. No reinventes combobox/listbox/dialog — son hard.
- **Focus management** built-in: modal trap, return focus on close, skip-links donde aplican.
- **Documenta el patrón a11y** en docs: cuándo usar `aria-label` vs `aria-labelledby`, cómo se anuncia el componente al SR.
- **Continuous monitoring**: Lighthouse CI en preview deploys + production audits trimestrales.

## Preguntas guía

- "¿Qué cubre el checklist a11y de un componente nuevo?"
- "¿Automatizas a11y testing en CI? ¿Qué herramientas?"
- "¿Tests manuales con screen reader — cuáles, cada cuánto?"
- "¿Usas componentes headless (Radix, React Aria)? ¿Para qué?"
- "Cuéntame del componente más complejo que has hecho a11y-compliant."
- "¿Cómo decides cuándo `aria-*` y cuándo HTML semántico?"

## Señales de seniority

- **Mid**: usa axe en Storybook, contraste OK, labels en forms.
- **Senior**: checklist a11y completo, screen reader testing manual cada release, conoce ARIA en profundidad, usa headless libs para components complejos.
- **Staff/Principal**: lidera a11y program (audit calendars, advisory board con users reales), define los componentes "core" que enforzan a11y, mide impacto en métricas de adopción + customer reviews, trabaja con legal/compliance (ADA, EAA).

## Anti-patterns

- "Lighthouse a11y en 95 — listo" — Lighthouse no detecta el 80% de los issues reales.
- `aria-hidden="true"` en cosas que el SR sí debería anunciar (errores, status).
- Reinventar combobox/dropdown sin testing keyboard exhaustivo.
- Focus management ad-hoc por componente (algunos trapean, otros no).
- Sin tests manuales con SR → solo "automatable issues" se detectan.
- A11y bug reports con "low priority" eternos.
- Componente "a11y por defecto" que pierde a11y cuando consumer lo customiza.

## Recursos

- *Inclusive Components* — Heydon Pickering (libro libre online).
- Sara Soueidan blog (componentes a11y patterns).
- Adrian Roselli blog (deep dive en patterns).
- Radix UI / React Aria / Headless UI source code (estudia patrones reales).
- WebAIM Screen Reader User Survey (data de usuarios reales).
- WAI-ARIA Authoring Practices (W3C oficial).
- *Form Design Patterns* — Adam Silver.
