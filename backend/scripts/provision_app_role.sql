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

-- Pre-create every known AGE label as the OWNER. Creating a NEW label
-- requires ownership of _ag_label_vertex/_ag_label_edge, which cvs_app
-- (rightly) lacks — without this, the first enrichment on a fresh DB dies
-- with "must be owner of table _ag_label_edge".
DO $$
DECLARE
    g text;
    vl text;
    el text;
BEGIN
    FOREACH g IN ARRAY ARRAY['universe_personal'] LOOP
        FOREACH vl IN ARRAY ARRAY[
            'Achievement','ArchitectureDecision','Artifact','Certification',
            'Course','Education','Evidence','Experience','Interest',
            'Language','Project','Skill'
        ] LOOP
            BEGIN
                PERFORM ag_catalog.create_vlabel(g, vl);
            EXCEPTION WHEN OTHERS THEN NULL;  -- already exists
            END;
        END LOOP;
        FOREACH el IN ARRAY ARRAY[
            'DEMONSTRATES','DERIVED_FROM','EVIDENCES_SIGNAL','LINKS_TO_ESCO',
            'MEMBER_OF','MERGED_INTO','OCCURRED_IN','PART_OF','PRODUCED',
            'RELATED_TO','SUPERSEDES','TOUCHED_IN','USES_TECH'
        ] LOOP
            BEGIN
                PERFORM ag_catalog.create_elabel(g, el);
            EXCEPTION WHEN OTHERS THEN NULL;  -- already exists
            END;
        END LOOP;
        -- the label tables AGE just created belong to the owner; grant DML
        EXECUTE format('GRANT USAGE ON SCHEMA %I TO cvs_app', g);
        EXECUTE format('GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA %I TO cvs_app', g);
    END LOOP;
END
$$;
