"""Snapshot-bound Python indexes and extraction attempts."""

import sqlalchemy as sa
from alembic import op

revision = "0002"
down_revision = "0001"


def upgrade():
    op.create_table(
        "source_indexes",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("snapshot_id", sa.String(64), sa.ForeignKey("snapshots.id"), nullable=False),
        sa.Column("version", sa.String(100), nullable=False),
        sa.Column("state", sa.String(30), nullable=False),
        sa.Column("report", sa.JSON(), nullable=True),
        sa.UniqueConstraint("snapshot_id", "version"),
    )
    op.create_table(
        "indexed_files",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("index_id", sa.String(36), sa.ForeignKey("source_indexes.id"), nullable=False),
        sa.Column("path", sa.String(512), nullable=False),
        sa.Column("result", sa.JSON(), nullable=False),
        sa.UniqueConstraint("index_id", "path"),
    )
    op.create_index("ix_indexed_files_index_id", "indexed_files", ["index_id"])
    op.create_table(
        "codeql_attempts",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("run_id", sa.String(36), sa.ForeignKey("runs.id"), nullable=False),
        sa.Column("result", sa.JSON(), nullable=False),
    )
    op.create_index("ix_codeql_attempts_run_id", "codeql_attempts", ["run_id"])


def downgrade():
    op.drop_table("codeql_attempts")
    op.drop_table("indexed_files")
    op.drop_table("source_indexes")
