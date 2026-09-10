"""Bound distinct triage requests even when configured monetary rates are zero."""

import sqlalchemy as sa
from alembic import op

revision = "0008"
down_revision = "0007"


def upgrade():
    op.add_column(
        "triage_budgets",
        sa.Column("max_requests", sa.Integer(), nullable=False, server_default="100"),
    )


def downgrade():
    with op.batch_alter_table("triage_budgets") as batch:
        batch.drop_column("max_requests")
