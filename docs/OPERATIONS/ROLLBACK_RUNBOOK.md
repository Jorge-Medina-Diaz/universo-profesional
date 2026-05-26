# Rollback Runbook — Universo Profesional v1.0

When a deploy causes critical degradation (DB errors, auth broken, checkout failing), follow this runbook to restore service quickly.

## Decision matrix

| Symptom | Immediate action | Rollback target |
|---------|-----------------|-----------------|
| Migration failed / DB schema bad | Stop deploy, do NOT restart backend | Pre-migration DB dump |
| Auth 500s for all users | Rollback backend image | Previous backend release |
| Stripe checkout broken | Rollback backend + verify webhook secret | Previous backend release |
| Frontend blank / 404s | Rollback frontend image | Previous frontend release |
| LLM provider down | Switch provider via secrets | No code rollback needed |

## 1-minute emergency rollback (Fly.io)

```bash
# Backend
flyctl deploy --config fly.toml --image cvs-saas-backend:previous-tag --remote-only

# Worker
flyctl deploy --config fly.worker.toml --image cvs-saas-backend:previous-tag --remote-only

# Frontend
flyctl deploy --config fly.frontend.toml --image cvs-saas-frontend:previous-tag --remote-only
```

> **Tip:** Tag images with the git short SHA before deploy so `previous-tag` is deterministic.

## 1-minute emergency rollback (Docker Compose)

```bash
# If you built images with explicit tags:
docker compose -f docker-compose.prod.yml pull backend:latest-stable frontend:latest-stable
docker compose -f docker-compose.prod.yml up -d backend worker frontend

# If using :latest, rebuild from the previous commit:
git checkout <previous-commit>
docker compose -f docker-compose.prod.yml build backend frontend
docker compose -f docker-compose.prod.yml up -d backend worker frontend
```

## Database rollback (schema migration gone wrong)

1. **Stop the backend** to prevent writes:
   ```bash
   flyctl scale count 0 --app cvs-saas-backend
   ```
2. **Restore from pre-deploy dump**:
   ```bash
   flyctl ssh console --app cvs-saas-db --command 'psql $DATABASE_URL < /tmp/pre-v1-backup.sql'
   ```
3. **Re-deploy the previous backend image**.
4. **Scale back up**:
   ```bash
   flyctl scale count 1 --app cvs-saas-backend
   ```

## After rollback

1. Pin the broken release in Sentry / issue tracker.
2. Write a postmortem in `docs/postmortems/YYYY-MM-DD-rollback.md`.
3. Fix forward in a branch; do NOT re-deploy the broken tag.
