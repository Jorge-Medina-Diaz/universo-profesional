# Database migrations

Alembic owns the schema. Every change goes through `alembic revision -m "..."`
followed by a manual edit if needed.

## Running in dev

```bash
docker compose exec backend alembic upgrade head
docker compose exec backend alembic current
```

## Running in production (Fly.io)

Migrations run inside the backend container so they share the connection
string. We do it BEFORE flipping traffic to a new release whenever the
release adds tables, columns, or indexes:

```bash
# 1. Take a backup (see BACKUP_RESTORE.md).
# 2. Apply migrations against the live DB.
flyctl ssh console --app cvs-saas-backend --command 'cd /app && alembic upgrade head'
# 3. Verify the schema is at the expected head.
flyctl ssh console --app cvs-saas-backend --command 'cd /app && alembic current'
# 4. Deploy the new app code.
flyctl deploy --config fly.toml --remote-only
```

## Rolling back

```bash
flyctl ssh console --app cvs-saas-backend --command 'cd /app && alembic downgrade -1'
```

Only safe when the migration is reversible AND the new code has been
rolled back too. Otherwise the running app may see a schema it doesn't
know how to talk to.

## Writing migrations

- ALWAYS add `op.execute` for index creation on big tables (≥10M rows) with
  `CONCURRENTLY` to avoid table locks.
- NEVER drop columns in the same release that stops writing to them — split
  into two releases (stop writing → drop next release).
- Test both `up` and `down` locally:
  ```bash
  docker compose exec backend alembic upgrade head
  docker compose exec backend alembic downgrade -1
  docker compose exec backend alembic upgrade head
  ```
- The CI matrix at `backend/tests/migrations/` runs this loop on every PR.

## Maintenance window

Long migrations (> 30 seconds of table locking) should run during a
maintenance window. Configure a 503 page in the frontend nginx and put
the backend in read-only mode (custom flag) — out of scope for this MVP
push but documented here as a placeholder.
