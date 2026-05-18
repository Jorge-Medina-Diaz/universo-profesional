-- Bootstrap extensions required by the application.
-- Alembic migration 0001 also ensures these, but creating here makes
-- pre-migration test fixtures and CI runs simpler.

CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS citext;
CREATE EXTENSION IF NOT EXISTS pgcrypto;
