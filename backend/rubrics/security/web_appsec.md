---
sector: security
slug: security/web_appsec
title: "AppSec: OWASP, vulnerability scanning, secure coding"
subtitle: "La parte de seguridad que vive en cada commit, no solo en pentest"
tags: [appsec, owasp, sast, dast, dependency, secret-scanning, csrf, xss, sqli]
weight: high
audience_levels: [mid, senior, staff]
when_to_ask:
  - "el usuario menciona seguridad de aplicaciones, AppSec, OWASP"
  - "habla de SAST/DAST, dependency scanning, secret scanning"
  - "describe vulns concretas (XSS, SQLi, CSRF, SSRF)"
---

## Criterios clave

- **OWASP Top 10** como base: Injection, Broken Auth, Sensitive Data Exposure, XXE, Broken Access Control, Security Misconfig, XSS, Insecure Deserialization, Components with Known Vulns, Insufficient Logging.
- **SAST en CI**: Semgrep, CodeQL, SonarQube. Falla PR cuando hay críticos.
- **Dependency scanning** (Snyk, GitHub Dependabot, npm audit, pip-audit): blocking en críticos, weekly review en altos.
- **Secret scanning** (gitleaks, TruffleHog, GitHub native): pre-commit hook + CI. Rotación automática si se filtra.
- **DAST + IAST** en staging: ZAP, Burp Pro, Veracode. Coverage de las rutas más expuestas.
- **Threat modeling** por feature significativa: STRIDE básico. ¿Quién es el atacante? ¿Qué quiere? ¿Cómo lo prevenimos / detectamos / respondemos?
- **Secure defaults**: framework con CSRF, XSS escaping, headers de seguridad (CSP, HSTS, X-Frame-Options) por defecto. NUNCA opt-in.
- **Pentests anuales** (o trimestral si maduros). Programa de bug bounty si el producto es grande/sensible.

## Preguntas guía

- "¿Tienes SAST en CI? ¿Qué tool, qué severidad bloquea PR?"
- "¿Has hecho threat modeling formal de una feature? Cuéntame."
- "¿Cómo gestionas las dependencias vulnerables — proceso, SLA de patch?"
- "Cuéntame del último incident de seguridad — ¿cómo se detectó, contuvo, comunicó?"
- "¿Tienes bug bounty? ¿Cuál fue la report más interesante?"
- "¿Cómo es el secure SDLC en tu equipo?"

## Señales de seniority

- **Mid**: conoce OWASP Top 10, framework con defaults seguros, dependency scan básico.
- **Senior**: threat modeling habitual, SAST + DAST en CI, runbook de incident response, secrets gestionados con vault, headers de seguridad correctos.
- **Staff/Principal**: gobierna AppSec program org-wide, security champions program, lidera respuestas a CVEs publicados, evangeliza secure-by-default en frameworks internos, gestiona pentests y bug bounty.

## Anti-patterns

- Construir HTML/SQL con concatenación de strings → injection.
- "Secure later" → vulnerabilidades acumulando.
- Sin CSP o CSP `unsafe-eval`/`unsafe-inline` → XSS trivial.
- Tokens en URLs (visibles en logs, history, referer headers).
- `Object.assign(user, req.body)` → mass assignment con propiedades sensibles.
- Logging full request bodies including passwords/tokens.
- "Validamos solo en frontend" → cualquier usuario con DevTools rompe.
- Ignorar warnings de SAST porque "el equipo está ocupado".

## Recursos

- OWASP Cheat Sheets (la biblia de practical AppSec).
- *The Web Application Hacker's Handbook* — Stuttard & Pinto.
- PortSwigger Web Security Academy (gratis, excelente).
- *Threat Modeling: Designing for Security* — Adam Shostack.
- Snyk / GitHub Advisory Database para vulns conocidas.
- Semgrep registry (rules abiertas).
- Krebs On Security para context industria.
