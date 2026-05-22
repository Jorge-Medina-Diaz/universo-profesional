---
sector: backend
slug: backend/auth_security
title: "Auth y seguridad backend"
subtitle: "Identidad, autorización, secretos: lo que un senior tiene interiorizado"
tags: [auth, jwt, oauth, session, rbac, abac, secrets, threat-model]
weight: high
audience_levels: [junior, mid, senior, staff]
when_to_ask:
  - "el usuario menciona auth, login, JWT, OAuth, sesiones"
  - "habla de roles, permisos, ACLs"
  - "describe manejo de secretos, API keys o credenciales"
---

## Criterios clave

- **Identidad vs autorización separadas**: un módulo que prueba "quién eres" (login, MFA, federación) y otro que decide "qué puedes hacer" (RBAC/ABAC, policy engine). Mezclarlos genera bugs sutiles.
- **Sesiones server-side por defecto**, JWT solo cuando hay razón real (cross-domain stateless, mobile sin cookies). JWTs sin revocación son una pesadilla en incidentes.
- **Tokens con expiración corta** (15min access, 7-30 días refresh con rotación + reuse detection). Cuando un refresh se usa dos veces, invalidar toda la cadena.
- **RBAC** para 80% de casos. **ABAC**/policy engine (Cedar, OPA, Casbin) cuando las reglas son data-driven (multi-tenant, scopes complejos).
- **Secrets nunca en código**. Vault/SOPS/cloud KMS. Rotación documentada con calendario. Logs no contienen secretos (scrubber en el logger).
- **Threat model explícito por feature**: STRIDE básico. ¿Spoofing? ¿Repudiation? ¿Information Disclosure? ¿DoS? ¿Privilege Escalation?
- **Defense in depth**: rate limiting, CAPTCHA en endpoints sensibles, RLS en la BD, headers de seguridad (CSP, HSTS, X-Frame-Options).

## Preguntas guía

- "¿Sesiones server-side o JWT? Cuéntame por qué."
- "¿Cómo gestionas la rotación de refresh tokens? ¿Detectas reuso?"
- "Si te dijese que vamos a tener N organizaciones con permisos a nivel recurso, ¿cómo modelarías la autorización?"
- "¿Dónde viven los secrets de producción? ¿Cómo se rotan?"
- "¿Has hecho threat modeling formal en alguna feature? Cuéntame."
- "¿Qué pasaría si te filtran 1M sesiones — cómo cortarías el blast radius?"

## Señales de seniority

- **Junior**: login + password hash + sesiones cookie. Sabe que JWT existe.
- **Mid**: OAuth providers, JWT con expiración, RBAC simple, almacenamiento de secrets en env vars (mejorable).
- **Senior**: refresh token rotation con reuse detection, RLS en Postgres o policy engine, rotación de keys con calendario, logging sin PII, headers de seguridad, conoce CSP en profundidad.
- **Staff/Principal**: zero-trust posture, federación SAML/OIDC, gestión de secrets multi-cloud (KMS hierarchies), threat models como práctica continua, runbooks para incidentes (token leak, account takeover, RCE).

## Anti-patterns

- Hash de password con MD5/SHA1 o sin salt — debe ser Argon2id/bcrypt/scrypt con coste calibrado.
- JWT con `alg: none` aceptado por la librería — vulnerabilidad clásica.
- Tokens largos (días) sin revocación → si se filtra uno, no puedes cortar.
- `Authorization` header logueado en plain text.
- "Solo el frontend valida que eres admin" — autorización siempre server-side.
- Secrets rotados nunca (`AWS_ACCESS_KEY_ID` de hace 4 años en prod).
- IDOR: endpoints que aceptan `?user_id=123` sin verificar pertenencia.

## Recursos

- OWASP Cheat Sheets (Auth, Session Management, Cryptographic Storage).
- *Web Application Hacker's Handbook* — la biblia de AppSec para devs.
- Curity Identity docs (OAuth/OIDC en profundidad).
- Cloudflare blog (TLS, rate limiting, DDoS at scale).
- *Identity & Data Security for Web Development* — Jonathan LeBlanc.
