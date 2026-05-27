# Despliegue local — guía rápida para probar

Esta guía cubre cómo levantar todo el stack en tu máquina y qué cosas opcionales puedes configurar para activar features completas (LLM real, pagos reales, emails reales, error reporting). Sin tocar nada, el sistema funciona en modo mock con todas las funcionalidades disponibles.

---

## TL;DR — arranque rápido

```bash
cd c:/Users/jorge/Desktop/Personal/CVs-SaaS
docker compose up -d
```

Espera 30-60 s. Abre:

- **App**: <http://localhost:5173>
- **API docs (Swagger)**: <http://localhost:8000/docs>
- **MailHog (correos capturados en dev)**: <http://localhost:8025>
- **Metrics Prometheus**: <http://localhost:8000/metrics>

Verificaciones rápidas:

```bash
curl http://localhost:8000/healthz   # liveness simple
curl http://localhost:8000/readyz    # comprueba DB + Redis + JWT keys + LLM
```

`/readyz` debe devolver `{"status":"ok","checks":{...}}`. Si está `degraded`, mira `docker logs cvs-backend`.

---

## Contenedores que arranca el compose

| Contenedor | Servicio | Puerto host | Notas |
|---|---|---|---|
| `cvs-postgres` | Postgres + pgvector | 5432 | RLS scoping per user. Datos en volumen `postgres_data`. |
| `cvs-redis` | Redis | 6379 | Cola Arq + rate-limit storage. |
| `cvs-mailhog` | SMTP de pruebas | 1025 (smtp) + 8025 (web) | Captura todos los emails. |
| `cvs-esco-seed` | Init container ESCO | — | Descarga (o usa muestra) e ingiere la ontología ESCO. Sale tras completar. |
| `cvs-backend` | FastAPI + Agno | 8000 | Hot-reload sobre `backend/src/`. |
| `cvs-worker` | Arq worker | — | 12+ tasks registradas. |
| `cvs-frontend` | Vite dev server | 5173 | Hot-reload sobre `frontend/src/`. |

Si quieres ver el estado:

```bash
docker ps --format "{{.Names}}\t{{.Status}}"
docker logs cvs-backend --tail 20 -f
```

---

## Lo que funciona **sin** API keys

| Feature | Estado | Detalle |
|---|---|---|
| Auth (register, login, refresh, reset, MFA stub) | ✅ | Verificación email vía MailHog. |
| Universo (entidades, búsqueda semántica) | ✅ | Embeddings con provider `deterministic` (sin OpenAI). |
| Jobs tracker | ✅ | Kanban + autopilot mock. |
| Documentos (CV/cover letter, plantillas) | ✅ | Renderizado WeasyPrint local. |
| Compartir documentos | ✅ | URL pública `/share/<token>`. |
| Onboarding LinkedIn ZIP | ✅ | Parse local sin API. |
| Chat (CopilotKit + Agno) | ⚠️ | Funciona pero el LLM falla loudly: necesitas `ANTHROPIC_API_KEY`. |
| Billing | ✅ | Modo mock — botón Upgrade simula el webhook. |
| Reminders + suggestions | ✅ | Engine local, sin LLM. |
| Search universe + readables | ✅ | |
| Notification center | ✅ | |
| Cookie consent banner | ✅ | |
| Security headers + rate limiting | ✅ | Verifica `curl -i http://localhost:8000/healthz`. |
| ESCO ontology | ✅ | Seeda automáticamente via `cvs-esco-seed` (sin intervención). |
| Discovery progress + SSE | ✅ | Funciona con datos locales. |

---

## Lo que necesita API keys (opcional)

Crea un archivo `.env` en la **raíz del repo** (al lado de `docker-compose.yml`) con solo las variables que quieras activar. Docker Compose ya lo lee automáticamente. Reinicia el container correspondiente con `docker restart cvs-backend cvs-worker` después de editarlo.

### 1. LLM real (chat agéntico funcional)

El chat necesita un LLM para responder. Sin clave usa un mock que falla en el primer mensaje.

```env
# Opción A — Anthropic (preferida, soporta prompt caching)
AGENTS_PROVIDER=anthropic
ANTHROPIC_API_KEY=sk-ant-api03-...

# Opción B — OpenAI
AGENTS_PROVIDER=openai
OPENAI_API_KEY=sk-...
```

**De dónde sacar la key**:
- Anthropic: <https://console.anthropic.com/settings/keys> — necesitas créditos ($5 gratis a veces, luego pago).
- OpenAI: <https://platform.openai.com/api-keys>.

Coste estimado de prueba: < $1 para una sesión de testing intensiva (Sonnet 4.6 cachea el system prompt).

### 2. Email real (Brevo)

Por defecto los emails se capturan en MailHog (<http://localhost:8025>). Si quieres probar el flujo completo con emails reales:

```env
EMAIL_PROVIDER=brevo
BREVO_API_KEY=xkeysib-...
EMAIL_FROM=test@tudominio-verificado.com
EMAIL_FROM_NAME=Universo Profesional
```

**De dónde sacar la key**:
- <https://app.brevo.com/settings/keys/api> — 300 emails/día gratis.
- Verifica un dominio sender o usa un email personal verificado.

### 3. Stripe real (pagos completos)

Por defecto el botón "Upgrade" simula un webhook localmente sin tarjeta. Si quieres probar Stripe Checkout real:

```env
STRIPE_PROVIDER=real
STRIPE_API_KEY=sk_test_...
STRIPE_WEBHOOK_SECRET=whsec_...
STRIPE_PRICE_PREMIUM_MONTHLY=price_...
STRIPE_PRICE_PRO_MONTHLY=price_...
STRIPE_SUCCESS_URL=http://localhost:5173/#/billing?success=1
STRIPE_CANCEL_URL=http://localhost:5173/#/billing?cancelled=1
```

**Setup paso a paso**:
1. Dashboard Stripe en **modo Test**: <https://dashboard.stripe.com/test/apikeys>.
2. Crea 2 productos con precios recurrentes mensuales (`Premium` €9.99/mes, `Pro` €19.99/mes). Copia los `price_...` IDs.
3. Para webhooks locales: instala Stripe CLI (`brew install stripe/stripe-cli/stripe`) y corre:
   ```bash
   stripe login
   stripe listen --forward-to http://localhost:8000/api/v1/billing/webhook
   ```
   El comando imprime un `whsec_...` — ese es tu `STRIPE_WEBHOOK_SECRET`.
4. Usa tarjeta de prueba `4242 4242 4242 4242`, cualquier fecha futura, CVC `123`.

### 4. Integraciones OAuth (GitHub / LinkedIn)

Sin estas, los botones de "Conectar GitHub" / "Conectar LinkedIn" no funcionarán.

```env
# GitHub
GITHUB_CLIENT_ID=Ov23li...
GITHUB_CLIENT_SECRET=...

# LinkedIn OIDC (sign-in + datos básicos)
LINKEDIN_CLIENT_ID=...
LINKEDIN_CLIENT_SECRET=...

# LinkedIn DMA (datos extendidos, solo Europa, requiere aprobación de LinkedIn)
LINKEDIN_DMA_ENABLED=true

# Bright Data (PRO tier — scraping LinkedIn de pago)
BRIGHTDATA_API_KEY=...
```

**Setup OAuth GitHub**:
1. <https://github.com/settings/developers> → New OAuth App.
2. Callback URL: `http://localhost:8000/api/v1/integrations/github/callback`.
3. Copia el Client ID + Client Secret.

**Setup OAuth LinkedIn**:
1. <https://www.linkedin.com/developers/apps> → Create app.
2. OAuth → Authorized redirect URL: `http://localhost:8000/api/v1/auth/linkedin/callback`.
3. Pide scopes: `openid profile email`.

### 5. Sentry (error reporting frontend + backend)

```env
# Backend
SENTRY_DSN=https://...@o....ingest.sentry.io/...

# Frontend — necesita VITE_ prefix porque va al cliente
VITE_SENTRY_DSN=https://...@o....ingest.sentry.io/...
```

La key `VITE_SENTRY_DSN` se aplica al rebuild del frontend (`docker compose build frontend` o restart con `docker restart cvs-frontend`). El backend la lee al startup.

Nota: Sentry frontend solo se inicia **después** de que el usuario acepte la cookie consent banner (bucket "Diagnóstico"). Ver `frontend/src/widgets/CookieConsentBanner.tsx`.

---

## Plantilla `.env` mínima para empezar

Copia esto a `.env` en la raíz, descomenta lo que vayas activando:

```env
# === LLM (necesario para que el chat responda) =================
# AGENTS_PROVIDER=anthropic
# ANTHROPIC_API_KEY=sk-ant-...

# === Email (opcional — MailHog captura todo en dev) ============
# EMAIL_PROVIDER=brevo
# BREVO_API_KEY=xkeysib-...

# === Stripe (opcional — mock funciona para probar UX) ===========
# STRIPE_PROVIDER=real
# STRIPE_API_KEY=sk_test_...
# STRIPE_WEBHOOK_SECRET=whsec_...
# STRIPE_PRICE_PREMIUM_MONTHLY=price_...
# STRIPE_PRICE_PRO_MONTHLY=price_...

# === GitHub integration (opcional) =============================
# GITHUB_CLIENT_ID=...
# GITHUB_CLIENT_SECRET=...

# === LinkedIn OIDC (opcional) ==================================
# LINKEDIN_CLIENT_ID=...
# LINKEDIN_CLIENT_SECRET=...

# === Bright Data (opcional, PRO tier) ==========================
# BRIGHTDATA_API_KEY=...

# === Sentry (opcional pero recomendable en staging) ============
# SENTRY_DSN=https://...
# VITE_SENTRY_DSN=https://...

# === ESCO ontology (ya es automática en Docker, solo para override) ===
# AUTO_SEED_ESCO=true          # semilla automática al arrancar en dev
# ESCO_VERSION=v1.1.1          # tag de release guardado en graph_ingest_meta
# ESCO_DOWNLOAD_URL=...        # URL alternativa del ZIP de ESCO
```

Tras editar `.env`:

```bash
docker compose restart backend worker frontend
```

---

## Flujos clave para probar

### Registro + verificación de email

1. <http://localhost:5173/#/register> → crear cuenta.
2. Abre MailHog (<http://localhost:8025>) → encontrarás el email de verificación.
3. Click en el enlace dentro del email.
4. Te lleva al frontend ya logueado.

**Atajo dev**: para saltar la verificación, activa `AUTO_VERIFY_EMAILS_IN_DEV=true` en tu `.env`. ⚠️ No lo dejes así si haces commit.

### Onboarding

Tras login: <http://localhost:5173/#/onboarding> te guía por subir un CV en PDF, conectar LinkedIn, o empezar de cero con el chat.

### Chat agéntico

Sin `ANTHROPIC_API_KEY` configurada el primer mensaje fallará. Con la clave: prueba `"yo sé python, fastapi, react, docker y typescript"` y verás aparecer un `SkillChipsCard` con las 5 skills detectadas.

### Generar CV adaptado

1. <http://localhost:5173/#/cv/new>
2. Pega una oferta de trabajo (el textarea trae un demo).
3. Elige plantilla (ATS / Modern / Minimal) + idioma + tono.
4. Click Generar. WeasyPrint renderiza el PDF en ~2-5 s.
5. Descarga PDF / DOCX / JSON.

### Job tracker + autopilot

1. <http://localhost:5173/#/jobs> → "Añadir oferta", pega un JD.
2. Click "Auto" → modal con preferencias → genera CV + cover letter + marca como aplicado.

### Multi-modal (chat + imagen)

Necesita `ANTHROPIC_API_KEY` (Claude Sonnet 4.6 con visión). Arrastra una imagen al chat (o pega con Ctrl+V o usa el botón de adjuntar 📎). El agente la analiza y clasifica.

### Billing mock

<http://localhost:5173/#/billing> → click "Mejorar a Premium" → te lleva al endpoint mock que simula un webhook y te upgradea inmediatamente.

### Billing real (con Stripe configurado)

Mismo flujo pero el backend redirige a Stripe Checkout real. Usa tarjeta `4242 4242 4242 4242`. Tras pagar, el webhook (vía `stripe listen`) actualiza tu plan.

---

## Comandos útiles

```bash
# Ver logs en tiempo real
docker logs cvs-backend -f
docker logs cvs-worker -f
docker logs cvs-frontend -f

# Restart un servicio (lee variables nuevas del .env)
docker compose restart backend

# Reset completo (borra volúmenes — pierdes datos)
docker compose down -v
docker compose up -d --build

# Aplicar migraciones nuevas manualmente
docker compose exec backend alembic upgrade head

# Entrar al backend para debugging
docker compose exec backend bash

# Generar un Fernet key fresco
docker compose exec backend python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"

# Verificar config de producción simulada
docker compose exec backend python -c "
from src.shared.config import get_settings
import os; os.environ['ENV']='production'
import src.shared.config as cfg; cfg.get_settings.cache_clear()
for e in cfg.get_settings().validate_production_ready(): print('-',e)
"

# Re-seed ESCO manualmente (o desde muestra si falla la descarga)
./scripts/seed-esco.sh

# Reset completo de ESCO (trunca + re-seed)
./scripts/reset-esco.sh
```

---

## Resolver problemas comunes

### Backend en restart loop

```bash
docker logs cvs-backend --tail 30
```

Si ves `ModuleNotFoundError: No module named 'slowapi'` o similar: la imagen está desactualizada. Rebuild:

```bash
docker compose build backend && docker compose up -d backend
```

### Frontend no carga

```bash
docker logs cvs-frontend --tail 30
```

Si ves errores de Vite sobre módulos: `docker exec cvs-frontend npm install`.

### `/readyz` devuelve `degraded`

Mira el campo `checks` en la respuesta. El que diga `error: ...` te indica qué dependencia falla.

### "Invalid credentials" al login

Posibles causas:
- La contraseña no cumple la política nueva (>=10 chars + mayúscula + dígito + no en lista común). Crea una cuenta nueva con `Welcome2026!` por ejemplo.
- Email no verificado. Mira MailHog (<http://localhost:8025>).

### Rate limit fired

```json
{"detail":"...","retry_after_seconds":900}
```

Espera 15 min o pon `RATE_LIMIT_ENABLED=false` en `.env` para desactivar temporalmente.

### El cookie banner no me deja seguir

Click "Aceptar todo" o "Solo necesarias". La decisión se guarda en localStorage. Para reiniciar: DevTools → Application → Local Storage → borra `cvs-saas-cookie-consent`.

---

## URLs por feature (mapa rápido)

| URL | Qué es |
|---|---|
| `/#/` | Landing pública |
| `/#/login` · `/#/register` | Auth |
| `/#/` (autenticado) | HomePage con chat |
| `/#/universe` | Tu universo profesional |
| `/#/jobs` | Job tracker (kanban) |
| `/#/cv/new` | Generador de CV / cover letter |
| `/#/documents` | Histórico de docs generados |
| `/#/compare` | Comparador A/B de 2 docs |
| `/#/connections` | GitHub / LinkedIn / PDF import |
| `/#/preferences` | Career preferences |
| `/#/settings` | Foto + cuenta + email prefs |
| `/#/billing` | Suscripción |
| `/#/share/<token>` | Página pública de un CV compartido |
| <http://localhost:8000/docs> | Swagger API |
| <http://localhost:8000/metrics> | Prometheus metrics |
| <http://localhost:8025> | MailHog (emails capturados) |

---

## Próximos pasos sugeridos para probar a fondo

1. **Sin tocar nada**: registra cuenta → verifica via MailHog → onboarding → genera 1 CV con la demo JD → comparte el link. Comprueba que TODO el flujo de generación funciona.
2. **Añade `ANTHROPIC_API_KEY`**: prueba el chat — pídele que te capture experiencia / skills / proyectos. Verifica los HITL cards (`propose_*`). Sube una imagen.
3. **Añade Stripe test keys**: prueba upgrade real con `4242 4242 4242 4242`. Verifica que el plan cambia y llega el email `payment_received`.
4. **Añade `SENTRY_DSN`**: provoca un error (ej. apaga Redis con `docker stop cvs-redis`) y verifica que aparece en tu dashboard Sentry.
5. **Lee la auditoría de producción** en `docs/OPERATIONS/DEPLOYMENT.md` y haz un dry-run de `flyctl deploy` cuando estés listo para poner esto online.

---

## Si algo no encaja

Pega la salida de:

```bash
docker compose ps
docker logs cvs-backend --tail 50
docker logs cvs-worker --tail 30
curl -s http://localhost:8000/readyz
```

…y te ayudo a triage.
