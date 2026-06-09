-- Provision the RLS-subject runtime role (cvs_app).
-- Idempotent: safe to re-run. Run as the owner role (cvs) on EVERY database
-- the app touches (dev: cvs; tests: cvs_test; prod: the prod DB).
--
-- Password: set via  ALTER ROLE cvs_app PASSWORD '<secret>'  separately —
-- this script never embeds credentials. In CI/dev a known password is set
-- by the caller.
--
-- Schemas covered:
--   public            — app tables (RLS-protected)
--   ai                — agno runtime tables (sessions/memories); created by
--                       the app, so CREATE is granted; pre-create as owner
--                       on fresh DBs (agno's create_schema fails as non-owner)
--   ag_catalog        — AGE catalog; label registration INSERTs into ag_label
--   universe_personal — AGE personal graph (label tables; CREATE for new labels)
--   universe_ontology — AGE ontology graph (read-mostly, but enrichment MERGEs)
--
-- NOTE: `LOAD 'age'` is superuser-only; the app skips it for non-superusers
-- (age_client.ensure_age_loaded) — the library auto-loads on first cypher().

DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'cvs_app') THEN
        CREATE ROLE cvs_app LOGIN NOSUPERUSER NOBYPASSRLS NOCREATEDB NOCREATEROLE;
    END IF;
END
$$;

CREATE SCHEMA IF NOT EXISTS ai;

GRANT USAGE ON SCHEMA public TO cvs_app;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO cvs_app;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO cvs_app;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO cvs_app;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT USAGE, SELECT ON SEQUENCES TO cvs_app;

GRANT USAGE, CREATE ON SCHEMA ai TO cvs_app;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA ai TO cvs_app;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA ai TO cvs_app;
ALTER DEFAULT PRIVILEGES IN SCHEMA ai GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO cvs_app;
ALTER DEFAULT PRIVILEGES IN SCHEMA ai GRANT USAGE, SELECT ON SEQUENCES TO cvs_app;

-- AGE may be absent on bare-postgres deploys; guard the graph grants.
DO $$
BEGIN
    IF EXISTS (SELECT FROM pg_namespace WHERE nspname = 'ag_catalog') THEN
        GRANT USAGE ON SCHEMA ag_catalog TO cvs_app;
        GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA ag_catalog TO cvs_app;
        GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA ag_catalog TO cvs_app;
        GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA ag_catalog TO cvs_app;
    END IF;
    IF EXISTS (SELECT FROM pg_namespace WHERE nspname = 'universe_personal') THEN
        GRANT USAGE, CREATE ON SCHEMA universe_personal TO cvs_app;
        GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA universe_personal TO cvs_app;
        GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA universe_personal TO cvs_app;
        ALTER DEFAULT PRIVILEGES IN SCHEMA universe_personal GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO cvs_app;
        ALTER DEFAULT PRIVILEGES IN SCHEMA universe_personal GRANT USAGE, SELECT ON SEQUENCES TO cvs_app;
    END IF;
    IF EXISTS (SELECT FROM pg_namespace WHERE nspname = 'universe_ontology') THEN
        GRANT USAGE, CREATE ON SCHEMA universe_ontology TO cvs_app;
        GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA universe_ontology TO cvs_app;
        GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA universe_ontology TO cvs_app;
        ALTER DEFAULT PRIVILEGES IN SCHEMA universe_ontology GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO cvs_app;
        ALTER DEFAULT PRIVILEGES IN SCHEMA universe_ontology GRANT USAGE, SELECT ON SEQUENCES TO cvs_app;
    END IF;
END
$$;
