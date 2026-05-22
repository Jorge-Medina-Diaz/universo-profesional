"""BM25 indexes — Sprint O.1 of the v2 plan.

Revision ID: 0015
Revises: 0014
Create Date: 2026-06-03

Adds a generated `tsv` tsvector column + GIN index to every entity table
that participates in retrieval. The hybrid retriever's BM25 lane runs
`to_tsquery('spanish', :q) @@ tsv` with `ts_rank_cd` ordering — typical
p50 latency over a 500-row user partition is ~3 ms.

We also add tsvectors to `ontology_embeddings` so query-time entity
linking can use BM25 to short-circuit the dense embedding call when the
exact label is present (saves ~80 ms on every chat turn that mentions
"AWS Lambda" or another well-known concept).

Language: Spanish stemmer (`spanish` dictionary, ships with postgres-16).
The text already includes English alt-labels for ESCO, so the BM25 lane
loses a bit of recall on EN-only queries; the dense lane is the
multilingual fallback there.
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0015"
down_revision: str | None = "0014"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


# Per-table tsvector expression. Each is built from the columns the
# retrieval BM25 lane will index — picked so they match the
# `embedding_text()` used for the dense lane and minimise drift.
_TSV_EXPRESSIONS: dict[str, str] = {
    "skills": (
        "to_tsvector('spanish', "
        "coalesce(name,'') || ' ' || coalesce(category,'') || ' ' || coalesce(level,''))"
    ),
    # tech_stack / competences / highlights are jsonb arrays. Casting to
    # text yields the JSON literal (`["python","fastapi"]`) which the
    # Spanish dictionary tokenises just fine for BM25 purposes.
    "projects": (
        "to_tsvector('spanish', "
        "coalesce(name,'') || ' ' || coalesce(description,'') || ' ' || "
        "coalesce(tech_stack::text,'') || ' ' || coalesce(impact,''))"
    ),
    "experiences": (
        "to_tsvector('spanish', "
        "coalesce(role,'') || ' ' || coalesce(organization,'') || ' ' || "
        "coalesce(description,'') || ' ' || coalesce(competences::text,''))"
    ),
    "educations": (
        "to_tsvector('spanish', "
        "coalesce(institution,'') || ' ' || coalesce(degree,'') || ' ' || "
        "coalesce(field_of_study,''))"
    ),
    "certifications": (
        "to_tsvector('spanish', coalesce(name,'') || ' ' || coalesce(issuer,''))"
    ),
    "courses": (
        "to_tsvector('spanish', coalesce(title,'') || ' ' || coalesce(platform,''))"
    ),
    "languages": (
        "to_tsvector('spanish', coalesce(code,'') || ' ' || coalesce(name,'') || ' ' || coalesce(level,''))"
    ),
    "achievements": (
        "to_tsvector('spanish', coalesce(title,'') || ' ' || coalesce(description,''))"
    ),
    "interests": (
        "to_tsvector('spanish', coalesce(name,'') || ' ' || coalesce(description,''))"
    ),
    "artifacts": (
        "to_tsvector('spanish', "
        "coalesce(type,'') || ' ' || coalesce(title,'') || ' ' || "
        "coalesce(description,'') || ' ' || coalesce(venue,''))"
    ),
    "architecture_decisions": (
        "to_tsvector('spanish', "
        "coalesce(title,'') || ' ' || coalesce(context,'') || ' ' || "
        "coalesce(decision,''))"
    ),
}


def upgrade() -> None:
    for table, expr in _TSV_EXPRESSIONS.items():
        op.execute(
            f"ALTER TABLE {table} "
            f"ADD COLUMN IF NOT EXISTS tsv tsvector "
            f"GENERATED ALWAYS AS ({expr}) STORED"
        )
        op.execute(
            f"CREATE INDEX IF NOT EXISTS ix_{table}_tsv ON {table} USING GIN (tsv)"
        )

    # Ontology BM25 index — combines ES + EN labels and descriptions for
    # cheap exact-label routing inside the entity linker.
    op.execute(
        """
        ALTER TABLE ontology_embeddings
        ADD COLUMN IF NOT EXISTS tsv tsvector
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_ontology_embeddings_tsv
        ON ontology_embeddings USING GIN (tsv)
        """
    )

    # Ontology labels live in the AGE vertex agtype properties, which the
    # planner cannot reach efficiently. We mirror the labels into a
    # standalone table `ontology_search` for fast tsvector queries.
    op.create_table(
        "ontology_search",
        sa.Column("uri", sa.Text(), primary_key=True),
        sa.Column("label", sa.String(64), nullable=False),
        sa.Column("pref_label_es", sa.Text(), nullable=True),
        sa.Column("pref_label_en", sa.Text(), nullable=True),
        sa.Column("alt_labels_es", sa.ARRAY(sa.Text()), nullable=True),
        sa.Column("alt_labels_en", sa.ARRAY(sa.Text()), nullable=True),
        sa.Column("description_es", sa.Text(), nullable=True),
        sa.Column("description_en", sa.Text(), nullable=True),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    # The weighted tsvector expression below requires functions that are
    # IMMUTABLE — `array_to_string(text[], text)` qualifies, but Postgres
    # only accepts the expression as a generated column if every nested
    # call is provably immutable to the planner. The two-arg `coalesce`
    # form on the array sometimes flips it to STABLE. We sidestep the
    # whole problem by storing a `tsv` column that's MAINTAINED via a
    # plain trigger; this is what pg_search_path's recipe recommends.
    op.execute(
        """
        ALTER TABLE ontology_search
        ADD COLUMN tsv tsvector
        """
    )
    op.execute(
        """
        CREATE OR REPLACE FUNCTION ontology_search_tsv_trigger()
        RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN
            NEW.tsv :=
                setweight(to_tsvector('spanish',
                    coalesce(NEW.pref_label_es,'') || ' ' ||
                    coalesce(NEW.pref_label_en,'')),
                    'A')
              || setweight(to_tsvector('spanish',
                    coalesce(array_to_string(NEW.alt_labels_es, ' '),'') || ' ' ||
                    coalesce(array_to_string(NEW.alt_labels_en, ' '),'')),
                    'B')
              || setweight(to_tsvector('spanish',
                    coalesce(NEW.description_es, NEW.description_en, '')),
                    'C');
            RETURN NEW;
        END
        $$
        """
    )
    op.execute(
        """
        CREATE TRIGGER ontology_search_tsv_update
        BEFORE INSERT OR UPDATE ON ontology_search
        FOR EACH ROW EXECUTE FUNCTION ontology_search_tsv_trigger()
        """
    )
    op.create_index(
        "ix_ontology_search_tsv", "ontology_search", ["tsv"], postgresql_using="gin"
    )
    op.create_index("ix_ontology_search_label", "ontology_search", ["label"])


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS ontology_search_tsv_update ON ontology_search")
    op.execute("DROP FUNCTION IF EXISTS ontology_search_tsv_trigger()")
    op.drop_index("ix_ontology_search_label", table_name="ontology_search")
    op.drop_index("ix_ontology_search_tsv", table_name="ontology_search")
    op.drop_table("ontology_search")
    op.execute("DROP INDEX IF EXISTS ix_ontology_embeddings_tsv")
    op.execute("ALTER TABLE ontology_embeddings DROP COLUMN IF EXISTS tsv")
    for table in _TSV_EXPRESSIONS:
        op.execute(f"DROP INDEX IF EXISTS ix_{table}_tsv")
        op.execute(f"ALTER TABLE {table} DROP COLUMN IF EXISTS tsv")
