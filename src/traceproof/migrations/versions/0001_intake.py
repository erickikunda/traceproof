"""Initial local intake schema. Keep migration definitions independent of ORM models."""

import sqlalchemy as sa
from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "repositories",
        sa.Column("id", sa.String(100), primary_key=True),
        sa.Column("owner", sa.String(200), nullable=False),
        sa.Column("classification", sa.String(100), nullable=False),
    )
    op.create_table(
        "imports",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("idempotency_key", sa.String(200), nullable=False, unique=True),
        sa.Column("request_sha256", sa.String(64), nullable=False),
        sa.Column("input_root", sa.String(4096), nullable=False),
        sa.Column("created_at", sa.String(40), nullable=False),
    )
    op.create_table(
        "snapshots",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("repo_id", sa.String(100), sa.ForeignKey("repositories.id"), nullable=False),
        sa.Column("manifest", sa.JSON, nullable=False),
    )
    op.create_table(
        "runs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("repo_id", sa.String(100), sa.ForeignKey("repositories.id"), nullable=False),
        sa.Column("state", sa.String(30), nullable=False),
        sa.Column("profile", sa.String(30), nullable=False),
        sa.Column("snapshot_id", sa.String(64), sa.ForeignKey("snapshots.id")),
        sa.Column("created_at", sa.String(40), nullable=False),
    )
    op.create_table(
        "import_items",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("import_id", sa.String(36), sa.ForeignKey("imports.id"), nullable=False),
        sa.Column("row_number", sa.Integer, nullable=False),
        sa.Column("state", sa.String(30), nullable=False),
        sa.Column("spec", sa.JSON),
        sa.Column("run_id", sa.String(36), sa.ForeignKey("runs.id")),
        sa.Column("error", sa.String(2000)),
        sa.Column("attempts", sa.Integer, nullable=False),
        sa.UniqueConstraint("import_id", "row_number"),
    )
    op.create_index("ix_import_items_import_id", "import_items", ["import_id"])
    op.create_index("ix_import_items_state", "import_items", ["state"])


def downgrade():
    for table in ["import_items", "runs", "snapshots", "imports", "repositories"]:
        op.drop_table(table)
