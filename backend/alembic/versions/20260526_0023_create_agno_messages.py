"""Create agno_messages table.

Expected by sliding_window.py and main.py startup index creation.
Agno's AsyncPostgresDb does not create this table automatically.
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "0023"
down_revision = "0022"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "agno_messages",
        sa.Column("id", sa.BigInteger(), sa.Identity(), primary_key=True),
        sa.Column("session_id", sa.Text(), nullable=False, index=True),
        sa.Column("role", sa.Text(), nullable=False),
        sa.Column("content", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        schema="public",
    )
    op.create_index(
        "ix_agno_messages_session",
        "agno_messages",
        ["session_id"],
        schema="public",
    )


def downgrade() -> None:
    op.drop_index("ix_agno_messages_session", table_name="agno_messages", schema="public")
    op.drop_table("agno_messages", schema="public")
