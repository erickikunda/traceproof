"""Append-only local operator review ledger."""

import sqlalchemy as sa
from alembic import op

revision = "0006"
down_revision = "0005"


def upgrade():
    op.create_table(
        "operator_reviews",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("candidate_id", sa.String(36), sa.ForeignKey("candidates.id"), nullable=False),
        sa.Column("bundle_id", sa.String(64), sa.ForeignKey("evidence_bundles.id"), nullable=False),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("request_key", sa.String(200), nullable=False),
        sa.Column("request_sha256", sa.String(64), nullable=False),
        sa.Column("content", sa.JSON(), nullable=False),
        sa.UniqueConstraint("candidate_id", "revision"),
        sa.UniqueConstraint("candidate_id", "request_key"),
    )
    op.create_index("ix_operator_reviews_candidate_id", "operator_reviews", ["candidate_id"])


def downgrade():
    op.drop_table("operator_reviews")
