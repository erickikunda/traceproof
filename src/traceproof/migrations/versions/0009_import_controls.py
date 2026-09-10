"""Append-only import dispatch pause/resume history."""

import sqlalchemy as sa
from alembic import op

revision = "0009"
down_revision = "0008"


def upgrade():
    op.create_table(
        "import_controls",
        sa.Column("import_id", sa.String(36), sa.ForeignKey("imports.id"), primary_key=True),
        sa.Column("revision", sa.Integer(), primary_key=True),
        sa.Column("state", sa.String(20), nullable=False),
        sa.Column("request_key", sa.String(200), nullable=False),
        sa.Column("reason", sa.String(1000), nullable=False),
        sa.Column("created_at", sa.String(40), nullable=False),
        sa.UniqueConstraint("import_id", "request_key"),
    )


def downgrade():
    op.drop_table("import_controls")
