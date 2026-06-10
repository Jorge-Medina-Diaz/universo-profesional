# Deploy

## Local production stack (verified 2026-06-10)

Prod-flavored images (immutable, nginx frontend, gunicorn backend, RLS-subject
DB role). Coexists with the dev volumes but NOT the dev containers (names
collide) — bring dev down first.

```bash
docker compose down                 # dev stack off (volumes preserved)
docker compose -f docker-compose.prod.yml -p cvs-prod --env-file .env.production build
bash scripts/deploy_local_prod.sh   # migrate → provision cvs_app → seed ESCO → up → smoke
```

| Surface | URL |
|---|---|
| App | http://localhost:8080 |
| API (direct) | http://localhost:8000 |
| Emails (verification etc.) | http://localhost:8025 (mailhog) |

Key facts the script encodes:
- **Migrations + ESCO seed run as the owner role `cvs` (`DATABASE_URL_SYNC`)**;
  the app/worker run as `cvs_app` (NOSUPERUSER NOBYPASSRLS → RLS is real).
  `CVS_APP_PASSWORD` lives in `.env.production`; the script ALTERs the role.
- ESCO seeding creates AGE labels → owner-only. `--sample-only` loads the
  bundled subset (~200 occupations; `/readyz` shows an advisory). For full
  coverage: download the ESCO CSV bundle and run `python -m scripts.seed_esco`
  with `ESCO_DOWNLOAD_URL`/local dir per the script header.
- `EMAIL_PROVIDER=mock` sends real SMTP to mailhog (it is NOT a no-op).
- Project name `cvs-prod` ⇒ volumes `cvs-prod_*`; dev data untouched.
- Back to dev: `docker compose -f docker-compose.prod.yml -p cvs-prod down`
  then `docker compose up -d`.

## Fly.io (first deploy runbook — needs your account)

Apps are pre-configured: `cvs-saas-backend` / `cvs-saas-worker` /
`cvs-saas-frontend` (region `mad`, `fly.toml` / `fly.worker.toml` /
`fly.frontend.toml`; API has `min_machines_running=2`).

1. `winget install flyctl` (or the install script) → `flyctl auth login`.
2. `flyctl apps create` the three names (or `flyctl launch --no-deploy` per
   config); `flyctl postgres create` + `attach` to backend AND worker;
   Upstash Redis via `flyctl redis create`.
3. Secrets on backend AND worker (names per fly.toml header):
   `TOKEN_ENCRYPTION_KEY, ANTHROPIC_API_KEY, OPENAI_API_KEY, BREVO_API_KEY,
   STRIPE_*, GITHUB_CLIENT_*` + `ENV=production`,
   `CANONICAL_BASE_URL/FRONTEND_BASE_URL/CORS_ORIGINS` (public URLs —
   startup REFUSES localhost values in production),
   `EMAIL_PROVIDER=brevo`, `STORAGE_PROVIDER=s3` + `S3_*` (Tigris:
   `flyctl storage create`; adapter verified against MinIO).
4. First-boot DB work (one-off machine or `flyctl ssh console`):
   `python -m alembic upgrade head`, then `psql < backend/scripts/`
   `provision_app_role.sql` + `ALTER ROLE cvs_app PASSWORD '…'`, then point
   the app's `DATABASE_URL` secret at `cvs_app` (keep the attached owner URL
   for migrations), then `python -m scripts.seed_esco` (full ESCO).
5. `flyctl deploy --config <each>.toml`; smoke: `/healthz`, `/readyz`,
   register→verify→login→chat.

Per-app deploys after that are just `flyctl deploy`. No GitHub remote is
configured on this repo, so CI (`.github/workflows/ci.yml`) only runs once
you push it somewhere — recommended before going public.
