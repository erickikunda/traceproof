"""Immutable local benchmark publications."""

import sqlalchemy as sa
from alembic import op

revision = "0007"
down_revision = "0006"


def upgrade():
    op.create_table(
        "benchmark_scorecards",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("dataset_id", sa.String(100), nullable=False),
        sa.Column("created_at", sa.String(40), nullable=False),
        sa.Column("content", sa.JSON(), nullable=False),
    )
    op.create_index("ix_benchmark_scorecards_dataset_id", "benchmark_scorecards", ["dataset_id"])


def downgrade():
    op.drop_table("benchmark_scorecards")
