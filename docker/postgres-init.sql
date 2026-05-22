-- Bootstrap extensions required by the application.
-- Alembic migration 0001 also ensures the vector/citext/pgcrypto trio,
-- and migration 0014 ensures AGE; we redo them here so pre-migration
-- fixtures and CI runs work out of the box.

CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS citext;
CREATE EXTENSION IF NOT EXISTS pgcrypto;
CREATE EXTENSION IF NOT EXISTS age;

-- AGE registers its graph DDL/DML under ag_catalog. Every connection that
-- runs Cypher must have ag_catalog in its search_path. Setting it at the
-- database level means we don't have to repeat `SET search_path` everywhere.
ALTER DATABASE cvs SET search_path = "$user", public, ag_catalog;

-- The two AGE graphs the application uses:
--   • universe_personal  — one logical graph holding every user's nodes
--     (multi-tenant via the user_id property on every vertex/edge).
--   • universe_ontology  — the shared ESCO + schema.org backbone.
-- Idempotent guards: AGE has no IF NOT EXISTS for create_graph, so we
-- swallow the duplicate error.
DO $$
BEGIN
    PERFORM create_graph('universe_personal');
EXCEPTION
    WHEN SQLSTATE 'XX000' THEN NULL;  -- already exists
    WHEN duplicate_schema THEN NULL;
END
$$;

DO $$
BEGIN
    PERFORM create_graph('universe_ontology');
EXCEPTION
    WHEN SQLSTATE 'XX000' THEN NULL;
    WHEN duplicate_schema THEN NULL;
END
$$;
