# Deployment — Fly.io (default) and VPS Docker (alternative)

## Pre-flight checklist

Before deploying for the first time, gather:

- Stripe live keys (`STRIPE_API_KEY`, `STRIPE_WEBHOOK_SECRET`) + 2 price IDs
- Brevo account + API key (`BREVO_API_KEY`)
- Anthropic API key
- A verified sending domain for `EMAIL_FROM` (SPF + DKIM in DNS)
- A custom domain (Cloudflare DNS is fine) pointed at the Fly apps
- Sentry DSN (optional but strongly recommended)

Generate the secrets that don't come from third parties:

```bash
# Fernet key for OAuth-token encryption.
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

## Fly.io (recommended)

We deploy 3 Fly apps:

| App                  | Config              | Memory | Notes                       |
|----------------------|---------------------|--------|-----------------------------|
| `cvs-saas-backend`   | `fly.toml`          | 1 GB   | HTTP service + JWT key vol  |
| `cvs-saas-worker`    | `fly.worker.toml`   | 1 GB   | Arq worker, no HTTP         |
| `cvs-saas-frontend`  | `fly.frontend.toml` | 256 MB | nginx + pre-rendered SPA    |

### One-time setup

```bash
flyctl auth login
flyctl apps create cvs-saas-backend
flyctl apps create cvs-saas-worker
flyctl apps create cvs-saas-frontend

# Provision Postgres + Redis (managed). pgvector is preinstalled.
flyctl postgres create --name cvs-saas-db --region mad --vm-size shared-cpu-1x --volume-size 10
flyctl postgres attach cvs-saas-db --app cvs-saas-backend
flyctl postgres attach cvs-saas-db --app cvs-saas-worker

# Upstash Redis (Fly partner). Returns a redis:// URL.
flyctl redis create --name cvs-saas-redis --region mad
flyctl redis attach cvs-saas-redis --app cvs-saas-backend
flyctl redis attach cvs-saas-redis --app cvs-saas-worker

# Persistent volumes for JWT keys + uploaded photos.
flyctl volumes create cvs_backend_var --app cvs-saas-backend --size 5 --region mad
flyctl volumes create cvs_worker_var --app cvs-saas-worker --size 5 --region mad
```

### Secrets

```bash
# Set ALL of these on backend + worker (worker can skip Stripe + CORS).
flyctl secrets set --app cvs-saas-backend \
  TOKEN_ENCRYPTION_KEY='...' \
  ANTHROPIC_API_KEY='...' \
  BREVO_API_KEY='...' \
  STRIPE_API_KEY='sk_live_...' \
  STRIPE_WEBHOOK_SECRET='whsec_...' \
  STRIPE_PRICE_PREMIUM_MONTHLY='price_...' \
  STRIPE_PRICE_PRO_MONTHLY='price_...' \
  STRIPE_SUCCESS_URL='https://app.universo.pro/#/billing?success=1' \
  STRIPE_CANCEL_URL='https://app.universo.pro/#/billing?cancelled=1' \
  CORS_ORIGINS='https://app.universo.pro' \
  CANONICAL_BASE_URL='https://api.universo.pro' \
  FRONTEND_BASE_URL='https://app.universo.pro' \
  EMAIL_FROM='no-reply@universo.pro' \
  SENTRY_DSN='https://...'

flyctl secrets set --app cvs-saas-worker \
  TOKEN_ENCRYPTION_KEY='...' \
  ANTHROPIC_API_KEY='...' \
  BREVO_API_KEY='...' \
  EMAIL_FROM='no-reply@universo.pro' \
  SENTRY_DSN='https://...'
```

### First deploy

```bash
flyctl deploy --config fly.toml --remote-only
flyctl deploy --config fly.worker.toml --remote-only
flyctl deploy --config fly.frontend.toml --remote-only \
  --build-arg VITE_API_BASE_URL='https://api.universo.pro' \
  --build-arg VITE_SENTRY_DSN='...' \
  --build-arg VITE_STRIPE_PUBLIC_KEY='pk_live_...'
```

### Custom domains

```bash
flyctl certs add app.universo.pro --app cvs-saas-frontend
flyctl certs add api.universo.pro --app cvs-saas-backend
```

Then point an `AAAA`/`A` record at `<app>.fly.dev` (or use Cloudflare CNAME with proxy off so Fly's TLS works).

### Migrations after a deploy

```bash
flyctl ssh console --app cvs-saas-backend --command 'cd /app && alembic upgrade head'
```

## VPS Docker (alternative)

```bash
# On the host:
git clone https://github.com/<you>/cvs-saas.git
cd cvs-saas
cp .env.example .env.production
# Edit .env.production with your real values.

docker compose -f docker-compose.prod.yml --env-file .env.production up -d
docker compose -f docker-compose.prod.yml exec backend alembic upgrade head
```

Put nginx (or Caddy) in front for TLS — point it at `backend:8000` and `frontend:8080`.

## Smoke test after deploy

```bash
curl -fsS https://api.universo.pro/readyz | jq    # checks DB+Redis+JWT
curl -fsSI https://app.universo.pro/ | head -20   # nginx serving + headers
```
