# RLS hardening (R2) — accurate status + completion runbook

> **Correction to commit f38a758.** That commit's message said R2 was
> "verified live." That was wrong and is corrected here: the policy migration
> is correct, but it does **not** yet enforce isolation, because the app
> connects to Postgres as a **superuser** (`cvs`, `rolsuper=t rolbypassrls=t`),
> and a superuser bypasses RLS unconditionally — even with `FORCE ROW LEVEL
> SECURITY`. Isolation only bites once the app connects as a **non-superuser**
> role. The remaining step is a credentials/infra change, deliberately not
> auto-applied (secrets), and documented below with the exact, already-tested
> commands.

## What IS done and committed (correct, reversible)

- **Migration 0032** (`f38a758`): every `<table>_user_isolation` policy rewritten
  to also pass when `app.bypass_rls = 'on'`, then `FORCE ROW LEVEL SECURITY` on
  all 37 user-scoped tables. Default-deny preserved (unset flag → falls through
  to the `user_id` check).
- **`set_rls_user`** (`shared/db.py`): per-user requests set
  `app.current_user_id` + `bypass_rls='off'`; the trusted service scope
  (`with_user_session(None)` — curator, reminders cron, hard-delete) sets
  `bypass_rls='on'`. All via `SET LOCAL` (transaction-scoped; can't leak across
  pooled connections).
- **Integration test** `tests/integration/test_rls_isolation.py` — asserts
  cross-tenant SELECT/UPDATE/DELETE return nothing and the service scope reads
  across users. **These tests only prove enforcement when run as a non-superuser
  role** (see below); under the current superuser they would pass the
  service-bypass case but the isolation cases depend on the role.

## What REMAINS — switch the app to a non-owner role (the actual enforcement)

A dedicated `cvs_app` role was created **and verified** in the dev database:

```
rolname=cvs_app  rolsuper=f  rolbypassrls=f
```

Verified as `cvs_app` (psql): a random `app.current_user_id` sees **0** rows in
`notes`; `app.bypass_rls='on'` sees all rows; pgvector operators work; the role
has SELECT/INSERT/UPDATE/DELETE on public tables + USAGE/SELECT on sequences.
So RLS **does** enforce correctly under this role — the only missing change is
pointing the app at it.

### Role provisioning (run as the `cvs` owner) — already applied in this dev DB

```sql
CREATE ROLE cvs_app LOGIN PASSWORD '<app-password>'
  NOSUPERUSER NOBYPASSRLS NOCREATEDB NOCREATEROLE;
GRANT USAGE ON SCHEMA public TO cvs_app;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO cvs_app;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO cvs_app;
ALTER DEFAULT PRIVILEGES IN SCHEMA public
  GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO cvs_app;
ALTER DEFAULT PRIVILEGES IN SCHEMA public
  GRANT USAGE, SELECT ON SEQUENCES TO cvs_app;
```

For a deployment that uses Apache AGE (this dev DB does **not** — it has only
`pgvector` + the `public` schema; the graph is computed via igraph snapshots in
Python), also: `GRANT USAGE ON SCHEMA ag_catalog TO cvs_app;` + SELECT on its
tables + EXECUTE on its functions.

### The flip (the secrets/infra change — NOT auto-applied)

Keep **migrations** on the owner (`cvs`, which has DDL rights) and switch only
the **app + worker runtime** to `cvs_app`:

- `docker-compose.yml` (and prod env): leave `DATABASE_URL_SYNC` (used by
  alembic) on `cvs`; point the app's `DATABASE_URL` at
  `postgresql+asyncpg://cvs_app:<app-password>@postgres:5432/cvs`.
- Provision `cvs_app` in prod the same way; store its password as a secret.
- Recreate backend + worker; run the isolation integration test — the
  cross-tenant cases now genuinely enforce.

This is the one R2 step that touches credentials, so it's left for an explicit
deploy change rather than applied blind.
