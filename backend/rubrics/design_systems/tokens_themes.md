---
sector: design_systems
slug: design_systems/tokens_themes
title: "Design tokens, theming, sincronización Figma↔código"
subtitle: "Hacer que diseño y código hablen el mismo lenguaje"
tags: [design-tokens, theme, figma, css-variables, naming, semantic]
weight: high
audience_levels: [mid, senior, staff]
when_to_ask:
  - "el usuario menciona design tokens, design system, theming"
  - "habla de Figma, semantic naming, color tokens"
  - "describe dark mode o multi-theme"
---

## Criterios clave

- **3 capas de tokens**: primitive (`gray-700`), semantic (`text-primary`, `border-subtle`), component (`button-bg-default`). El consumer solo usa semantic+component; primitive es interno al sistema.
- **Naming consistente**: `[purpose]-[variant]-[state]` (`text-link-hover`). Nada de `red`, `dark-blue` en componentes — son colores, no roles.
- **Source of truth única**: Style Dictionary, Theo, Figma Tokens plugin → genera CSS/JS/iOS/Android. Manual sync no escala.
- **Theme switching como dato**: `data-theme="dark"` + CSS vars. NO duplicar componentes por tema. Theme = paleta + un par de overrides puntuales.
- **Versionado del sistema**: SemVer del package del design system. Major = breaking (token removed/renamed). Communicar con changelog.
- **Composición vs override**: tokens componibles (`--spacing-md = calc(var(--base) * 2)`). Avoid magic numbers en consumer code.
- **Accessibility built-in**: contrast pairs validados (text-on-surface, focus rings AA). Cambiar paleta no debe romper AA.
- **Documentation con ejemplos**: Storybook + design docs viven en el mismo repo. Sin doc viva, el sistema se ignora.

## Preguntas guía

- "¿Capas de tokens — primitive, semantic, component? ¿Cómo las separas?"
- "¿Cuál es la source of truth — Figma, código, herramienta intermedia?"
- "¿Cómo gestionas el theme switching (light/dark, brand variants)?"
- "Cuéntame del proceso cuando cambias un token semantic — ¿cómo se propaga?"
- "¿Tu design system tiene SemVer? ¿Cómo comunicas breaking changes?"
- "¿Cómo validas la accesibilidad (contrast pairs) al cambiar paleta?"

## Señales de seniority

- **Mid**: usa CSS vars + Tailwind config, conoce design tokens conceptualmente, theme dark básico.
- **Senior**: 3 capas de tokens, source of truth única (Style Dictionary), SemVer del sistema, theme switching como dato, contrast pairs documentados.
- **Staff/Principal**: gobierna el design system org-wide, coordina con design team, mide adopción (% de componentes en producción usando el system), planifica migraciones tras breaking changes, multi-brand multi-platform.

## Anti-patterns

- Componente con `style={{ color: '#3b82f6' }}` hardcoded — bypass del sistema.
- Tokens con nombre de color (`blue-500`) usados directamente en consumer — cambiar paleta requiere search-replace.
- Múltiples sources of truth (Figma values diferentes del código).
- Theme dark implementado duplicando componentes en lugar de variables.
- Sin versionado → breaking changes silenciosos.
- Sin Storybook / docs → adopción baja.
- "El designer dice que ahora es #ff6600" sin pasar por el sistema.

## Recursos

- *Design Tokens Format* — comunidad/W3C draft.
- Brad Frost: *Atomic Design* (libro y blog).
- Style Dictionary docs (Amazon).
- Figma Tokens / Tokens Studio.
- Nathan Curtis: *EightShapes* (medium articles, gold standard).
- Material Design 3 docs (referencia de tokens muy completa).
- Stripe / Atlassian / GitHub Primer design system case studies.
