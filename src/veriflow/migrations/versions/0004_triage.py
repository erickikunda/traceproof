"""Immutable evidence bundles and conservative model-cost ledger."""

import sqlalchemy as sa
from alembic import op

revision = "0004"
down_revision = "0003"


def upgrade():
    op.create_table(
        "evidence_bundles",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("candidate_id", sa.String(36), sa.ForeignKey("candidates.id"), nullable=False),
        sa.Column("content", sa.JSON(), nullable=False),
    )
    op.create_index("ix_evidence_bundles_candidate_id", "evidence_bundles", ["candidate_id"])
    op.create_table(
        "triage_budgets",
        sa.Column("run_id", sa.String(36), sa.ForeignKey("runs.id"), primary_key=True),
        sa.Column("limit_micro_usd", sa.BigInteger(), nullable=False),
    )
    op.create_table(
        "triage_calls",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("run_id", sa.String(36), sa.ForeignKey("runs.id"), nullable=False),
        sa.Column("bundle_id", sa.String(64), sa.ForeignKey("evidence_bundles.id"), nullable=False),
        sa.Column("request_key", sa.String(200), nullable=False),
        sa.Column("request_sha256", sa.String(64), nullable=False),
        sa.Column("created_at", sa.String(40), nullable=False),
        sa.Column("state", sa.String(40), nullable=False),
        sa.Column("charged_micro_usd", sa.BigInteger(), nullable=False),
        sa.Column("result", sa.JSON(), nullable=False),
        sa.UniqueConstraint("run_id", "request_key"),
    )
    op.create_index("ix_triage_calls_run_id", "triage_calls", ["run_id"])


def downgrade():
    op.drop_table("triage_calls")
    op.drop_table("triage_budgets")
    op.drop_table("evidence_bundles")
