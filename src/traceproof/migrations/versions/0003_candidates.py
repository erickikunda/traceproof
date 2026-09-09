"""Durable static-analysis attempts and unreviewed candidates."""

import sqlalchemy as sa
from alembic import op

revision = "0003"
down_revision = "0002"


def upgrade():
    op.create_table(
        "scan_attempts",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("run_id", sa.String(36), sa.ForeignKey("runs.id"), nullable=False),
        sa.Column("created_at", sa.String(40), nullable=False),
        sa.Column("report", sa.JSON(), nullable=False),
    )
    op.create_index("ix_scan_attempts_run_id", "scan_attempts", ["run_id"])
    op.create_table(
        "candidates",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("attempt_id", sa.String(36), sa.ForeignKey("scan_attempts.id"), nullable=False),
        sa.Column("fingerprint", sa.String(64), nullable=False),
        sa.Column("evidence", sa.JSON(), nullable=False),
        sa.UniqueConstraint("attempt_id", "fingerprint"),
    )
    op.create_index("ix_candidates_attempt_id", "candidates", ["attempt_id"])


def downgrade():
    op.drop_table("candidates")
    op.drop_table("scan_attempts")
