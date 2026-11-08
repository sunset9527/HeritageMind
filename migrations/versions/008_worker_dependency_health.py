"""add safe worker dependency health summaries

Revision ID: 008
Revises: 007
Create Date: 2026-10-31
"""

from alembic import op
import sqlalchemy as sa


revision = "008"
down_revision = "007"
branch_labels = None
depends_on = None


def _columns() -> set[str]:
    return {column["name"] for column in sa.inspect(op.get_bind()).get_columns("worker_heartbeats")}


def upgrade() -> None:
    columns = _columns()
    with op.batch_alter_table("worker_heartbeats") as batch_op:
        if "status" not in columns:
            batch_op.add_column(sa.Column("status", sa.String(length=20), nullable=False, server_default="unknown"))
        if "dependencies_json" not in columns:
            batch_op.add_column(sa.Column("dependencies_json", sa.Text(), nullable=False, server_default="{}"))
        if "last_error_code" not in columns:
            batch_op.add_column(sa.Column("last_error_code", sa.String(length=80), nullable=True))


def downgrade() -> None:
    columns = _columns()
    with op.batch_alter_table("worker_heartbeats") as batch_op:
        for name in ("last_error_code", "dependencies_json", "status"):
            if name in columns:
                batch_op.drop_column(name)
