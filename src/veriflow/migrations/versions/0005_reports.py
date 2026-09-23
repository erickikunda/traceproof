"""Immutable repository report projections."""

import sqlalchemy as sa
from alembic import op

revision = "0005"
down_revision = "0004"


def upgrade():
    op.create_table(
        "published_reports",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("run_id", sa.String(36), sa.ForeignKey("runs.id"), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("input_digest", sa.String(64), nullable=False),
        sa.Column("created_at", sa.String(40), nullable=False),
        sa.Column("content", sa.JSON(), nullable=False),
        sa.UniqueConstraint("run_id", "version"),
        sa.UniqueConstraint("run_id", "input_digest"),
    )
    op.create_index("ix_published_reports_run_id", "published_reports", ["run_id"])


def downgrade():
    op.drop_table("published_reports")
