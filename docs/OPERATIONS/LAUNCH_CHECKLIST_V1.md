# Launch Checklist — Universo Profesional v1.0

Use this checklist before every production deploy. Items are ordered by risk: infra first, then data, then code.

## Pre-flight (1–2 days before)

- [ ] **Secrets audit** — there is no audit script; grep `.env.production` by hand
  (`grep -nE 'cvs_dev_password|localhost|_IN_DEV=true|_ECHO=true' .env.production` must print nothing).
  Most of these are also enforced at boot by `validate_production_ready()` in
  `backend/src/shared/config.py`, which refuses to start the app when `ENV=production`:
  - [ ] `DATABASE_URL` does NOT contain `cvs_dev_password`
  - [ ] `CORS_ORIGINS` does NOT contain `localhost`
  - [ ] `CANONICAL_BASE_URL` and `FRONTEND_BASE_URL` are HTTPS public URLs
  - [ ] `TOKEN_ENCRYPTION_KEY` is a real Fernet key (not empty)
  - [ ] `AUTO_VERIFY_EMAILS_IN_DEV=false`
  - [ ] `DATABASE_ECHO=false`
- [ ] **Stripe live mode** — confirm:
  - [ ] `STRIPE_PROVIDER=real`
  - [ ] `STRIPE_API_KEY` starts with `sk_live_`
  - [ ] `STRIPE_WEBHOOK_SECRET` is set
  - [ ] Price IDs match the live Stripe dashboard
- [ ] **Email provider** — confirm `EMAIL_PROVIDER=brevo` (the only real provider; `mock` is rejected in prod)
- [ ] **LLM provider** — confirm `ANTHROPIC_API_KEY` or `OPENAI_API_KEY` is set
- [ ] **Domain + DNS** — verify TLS certificates and `AAAA`/`A` records
- [ ] **Sentry DSN** — optional but recommended for error tracking

## Database (day of deploy)

- [ ] **Backup** — take a manual snapshot before migrations:
  ```bash
  flyctl ssh console --app cvs-saas-backend --command 'pg_dump $DATABASE_URL > /tmp/pre-v1-backup.sql'
  ```
  Or for Docker: `docker compose -f docker-compose.prod.yml exec postgres pg_dump ...`
- [ ] **Migrations** — run `alembic upgrade head` and verify no errors
- [ ] **Smoke test** — `curl -fsS https://api.universo.pro/readyz | jq` returns 200

## Deploy sequence

1. **Backend** — deploy first so the API is ready when the frontend hits it
2. **Worker** — deploy after backend (same image, different command)
3. **Frontend** — deploy last; verify build args (`VITE_API_BASE_URL`, etc.)

## Post-deploy verification (5 min)

- [ ] `/healthz` → 200
- [ ] `/readyz` → 200 (DB + Redis + JWT keys)
- [ ] `/metrics` → Prometheus metrics exposed
- [ ] Register → Verify → Login flow works on production domain
- [ ] Generate a test CV (mock LLM is OK for smoke test)
- [ ] Stripe checkout mock page loads (or test with Stripe test mode first)
- [ ] Sentry receives a test event (optional)

## Rollback plan

If anything fails post-deploy, see `ROLLBACK_RUNBOOK.md`.
