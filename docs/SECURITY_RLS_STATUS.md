# RLS hardening (R2) — COMPLETE in dev; prod = one secrets change

> **Status 2026-06-09:** the app + worker now connect as **`cvs_app`**
> (`NOSUPERUSER NOBYPASSRLS`) in docker-compose dev, and tenant isolation is
> **enforced and live-verified** (isolation suite 4/4 as `cvs_app`; full
> smoke: register → login → refresh → note write → coherence upsert →
> AGE vertex; worker crons clean). Prod needs the same flip (below).

## What enforcement surfaced (all fixed — keep these in mind for new code)

The superuser connection had been masking four real defect classes:

1. **Policy `''::uuid` poison** — `RESET app.current_user_id` *defines* an
   unset custom GUC as `''` session-wide on the pooled connection, and SQL
   `OR` does not short-circuit, so every policy's
   `current_setting(...)::uuid` cast could explode mid-request. Fixed by
   **migration 0039**: every user policy is now the canonical
   `bypass = 'on' OR NULLIF(current_setting(...), '')::uuid = user_id`,
   and `set_rls_user(None)` uses `SET LOCAL app.current_user_id = ''`
   (txn-scoped) instead of `RESET` (`shared/db.py`).
2. **Six tables missed by 0032** — policies named `*_rls` (not
   `*_user_isolation`): community_summaries, entity_quarantine,
   graph_edge_audit, graph_entity_embeddings, graph_esco_links,
   llm_usage_logs. They had no bypass arm (service-scope workers silently
   read 0 rows) and no FORCE. Migration 0039 discovers policies by their
   *expression* (`LIKE '%app.current_user_id%'`), not by name, so both
   naming conventions are covered — including on fresh-DB runs.
3. **Pre-auth identity flows wrote without any RLS context** — register
   (trial subscription), login/MFA (refresh token), refresh (rotation),
   verify/reset (email tokens). These endpoints ARE the trust boundary, so
   they now run in the trusted service scope via `PreAuthSessionDep`
   (`identity/interfaces/api/deps.py`); every authenticated surface keeps
   the per-user context from `current_user_id()`.
4. **`LOAD 'age'` is superuser-only** — even from `$libdir/plugins`.
   `ensure_age_loaded` (`graph/infrastructure/age_client.py`) now issues the
   explicit LOAD only for superusers; for `cvs_app` the library auto-loads
   on the first `cypher()` C-function call. No config change needed.

### Related landmine fixed while flipping: cluster `search_path`

`docker/postgres.Dockerfile` used to set `search_path =
'ag_catalog, "$user", public'` cluster-wide. Any database created without a
per-DB override (e.g. a fresh `cvs_test`) sent every unqualified
`CREATE TABLE` — **including `alembic_version` itself** — into `ag_catalog`,
silently producing a broken from-scratch schema. The image now ships
`'"$user", public, ag_catalog'` (Cypher only needs ag_catalog *present*).
For existing clusters: `ALTER DATABASE <db> SET search_path = "$user",
public, ag_catalog;` before migrating any new database.

## Role provisioning — one idempotent script

`backend/scripts/provision_app_role.sql` creates `cvs_app` and grants on
**all five schemas** the app touches (`public`, `ai` for agno — pre-created
there because agno's `create_schema=True` fails as non-owner — `ag_catalog`,
`universe_personal`, `universe_ontology`). Run as the owner on every
database (dev `cvs`, `cvs_test`, prod), then set the password:

```bash
docker exec -i cvs-postgres psql -U cvs -d cvs  < backend/scripts/provision_app_role.sql
docker exec cvs-postgres psql -U cvs -c "ALTER ROLE cvs_app PASSWORD '<secret>'"
```

## The flip itself

Keep **migrations** on the owner (`cvs`, DDL rights); point only the
**app + worker runtime** at `cvs_app`:

- dev: done in `docker-compose.yml` (backend + worker `DATABASE_URL` →
  `cvs_app`; `DATABASE_URL_SYNC` stays on `cvs`; `esco-seed` stays on `cvs`).
- prod (Fly): provision the role + grants on the prod DB, then
  `fly secrets set DATABASE_URL=postgresql+asyncpg://cvs_app:...` on the
  API and worker apps. `DATABASE_URL_SYNC` (alembic release step) stays on
  the owner.

## Verification (re-run after any schema/work)

```bash
# Isolation suite as the subject role (in-container; cvs_test migrated to head)
MSYS_NO_PATHCONV=1 docker exec \
  -e PYTHONPATH=/app/.local/lib/python3.13/site-packages \
  -e DATABASE_URL=postgresql+asyncpg://cvs_app:<pwd>@postgres:5432/cvs_test \
  -e DATABASE_URL_SYNC=postgresql://cvs:cvs_dev_password@postgres:5432/cvs_test \
  cvs-backend python -m pytest tests/integration/test_rls_isolation.py -q
```

A missed GRANT on a future table surfaces as `InsufficientPrivilegeError
42501` at runtime; `ALTER DEFAULT PRIVILEGES` in the provisioning script
covers tables created by future **owner-run migrations** automatically.
Tables created at runtime by `cvs_app` itself (new AGE label tables) are
owned by `cvs_app` — no extra grant needed.

Known benign artifact: agno may try `CREATE INDEX IF NOT EXISTS` on its own
tables at startup; Postgres checks ownership *before* the existence
shortcut, so `main._ensure_agno_indexes` probes `pg_indexes` first. If agno
version upgrades ever need new tables/columns in schema `ai`, run that
startup once with an owner `DATABASE_URL` (or grant ownership), then flip
back.
