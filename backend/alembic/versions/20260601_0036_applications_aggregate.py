"""Applications first-class pipeline aggregate (F).

Revision ID: 0036
Revises: 0035
Create Date: 2026-06-01

The Kanban tracker lived in jobs.description_parsed._tracker (JSONB). Promote it
to the typed `applications` table (which already exists from 0001, RLS-enabled +
FORCEd by 0032 — so this ALTERs, never CREATEs it) and add `job_requirements`.
Backfills existing _tracker blobs + parsed JD requirements. The _tracker key is
intentionally LEFT in place (jobs_router dual-reads it as a fallback); a later
cleanup migration strips it once the aggregate is proven in prod.
"""
from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0036"
down_revision: str | None = "0035"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_REQ_ISOLATION = (
    "(current_setting('app.bypass_rls'::text, true) = 'on' "
    "OR (current_setting('app.current_user_id'::text, true))::uuid = user_id)"
)


def upgrade() -> None:
    # 1) Evolve the existing applications table (do NOT recreate).
    op.execute(
        """
        ALTER TABLE applications
            ALTER COLUMN stage SET DEFAULT 'saved',
            ADD COLUMN IF NOT EXISTS status text,
            ADD COLUMN IF NOT EXISTS position double precision,
            ADD COLUMN IF NOT EXISTS applied_at timestamptz,
            ADD COLUMN IF NOT EXISTS screen_at timestamptz,
            ADD COLUMN IF NOT EXISTS interview_at timestamptz,
            ADD COLUMN IF NOT EXISTS offer_at timestamptz,
            ADD COLUMN IF NOT EXISTS closed_at timestamptz,
            ADD COLUMN IF NOT EXISTS closed_reason text,
            ADD COLUMN IF NOT EXISTS match_score integer,
            ADD COLUMN IF NOT EXISTS match jsonb,
            ADD COLUMN IF NOT EXISTS contacts jsonb NOT NULL DEFAULT '[]'::jsonb
        """
    )
    op.execute(
        "ALTER TABLE applications DROP CONSTRAINT IF EXISTS applications_stage_chk"
    )
    op.execute(
        "ALTER TABLE applications ADD CONSTRAINT applications_stage_chk "
        "CHECK (stage IN ('saved','applied','screen','interview','offer','closed'))"
    )
    op.execute("CREATE INDEX IF NOT EXISTS ix_applications_job ON applications(job_id)")
    op.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS uq_applications_user_job "
        "ON applications(user_id, job_id) WHERE job_id IS NOT NULL"
    )

    # 2) job_requirements (must_have | nice_to_have | ats_keyword), RLS like 0032.
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS job_requirements (
            id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            job_id uuid NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
            kind text NOT NULL,
            label text NOT NULL,
            created_at timestamptz NOT NULL DEFAULT now()
        )
        """
    )
    op.execute("CREATE INDEX IF NOT EXISTS ix_job_requirements_job ON job_requirements(job_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_job_requirements_user ON job_requirements(user_id)")
    op.execute("ALTER TABLE job_requirements ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE job_requirements FORCE ROW LEVEL SECURITY")
    op.execute('DROP POLICY IF EXISTS "job_requirements_user_isolation" ON job_requirements')
    op.execute(
        'CREATE POLICY "job_requirements_user_isolation" ON job_requirements '
        f"USING ({_REQ_ISOLATION}) WITH CHECK ({_REQ_ISOLATION})"
    )

    # 3) Backfill applications from jobs._tracker (one row per tracked job).
    op.execute(
        """
        INSERT INTO applications (
            id, user_id, job_id, document_id, stage, status, position, notes,
            applied_at, interview_at, offer_at, closed_at, closed_reason,
            next_action_at, match_score, match, created_at, updated_at
        )
        SELECT
            gen_random_uuid(), j.user_id, j.id,
            (SELECT d.id FROM documents d WHERE d.job_id = j.id
             ORDER BY d.created_at DESC LIMIT 1),
            CASE t->>'status'
                WHEN 'applied' THEN 'applied'
                WHEN 'interviewing' THEN 'interview'
                WHEN 'offer' THEN 'offer'
                WHEN 'rejected' THEN 'closed'
                WHEN 'archived' THEN 'closed'
                ELSE 'saved'
            END,
            t->>'status',
            NULLIF(t->>'position','')::double precision,
            t->>'notes',
            NULLIF(t->>'applied_at','')::timestamptz,
            CASE WHEN t->>'status' = 'interviewing' THEN now() END,
            CASE WHEN t->>'status' = 'offer' THEN now() END,
            CASE WHEN t->>'status' IN ('rejected','archived') THEN now() END,
            CASE WHEN t->>'status' IN ('rejected','archived') THEN t->>'status' END,
            NULLIF(t->>'next_action_at','')::timestamptz,
            NULLIF(t->>'match_score','')::integer,
            t->'match',
            j.created_at, now()
        FROM jobs j
        CROSS JOIN LATERAL (SELECT j.description_parsed->'_tracker' AS t) x
        WHERE j.description_parsed ? '_tracker'
        ON CONFLICT (user_id, job_id) WHERE job_id IS NOT NULL DO NOTHING
        """
    )

    # 4) Backfill job_requirements from parsed JD arrays.
    for src_key, kind in (
        ("must_haves", "must_have"),
        ("nice_to_haves", "nice_to_have"),
        ("ats_keywords", "ats_keyword"),
    ):
        op.execute(
            f"""
            INSERT INTO job_requirements (id, user_id, job_id, kind, label, created_at)
            SELECT gen_random_uuid(), j.user_id, j.id, '{kind}', x.label, now()
            FROM jobs j
            CROSS JOIN LATERAL jsonb_array_elements_text(
                coalesce(j.description_parsed->'{src_key}', '[]'::jsonb)
            ) AS x(label)
            WHERE jsonb_typeof(j.description_parsed->'{src_key}') = 'array'
              AND x.label <> ''
            """
        )


def downgrade() -> None:
    op.execute('DROP POLICY IF EXISTS "job_requirements_user_isolation" ON job_requirements')
    op.execute("DROP TABLE IF EXISTS job_requirements")
    op.execute("DROP INDEX IF EXISTS uq_applications_user_job")
    op.execute("DROP INDEX IF EXISTS ix_applications_job")
    op.execute("ALTER TABLE applications DROP CONSTRAINT IF EXISTS applications_stage_chk")
    op.execute(
        """
        ALTER TABLE applications
            DROP COLUMN IF EXISTS status,
            DROP COLUMN IF EXISTS position,
            DROP COLUMN IF EXISTS applied_at,
            DROP COLUMN IF EXISTS screen_at,
            DROP COLUMN IF EXISTS interview_at,
            DROP COLUMN IF EXISTS offer_at,
            DROP COLUMN IF EXISTS closed_at,
            DROP COLUMN IF EXISTS closed_reason,
            DROP COLUMN IF EXISTS match_score,
            DROP COLUMN IF EXISTS match,
            DROP COLUMN IF EXISTS contacts
        """
    )
    # Note: the backfilled applications rows are left in place on downgrade
    # (harmless; the table predates this migration). A full revert would also
    # DELETE rows where status came from _tracker, but that risks data loss if
    # the app already wrote new applications — so we keep them.
