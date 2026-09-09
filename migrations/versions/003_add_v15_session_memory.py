"""add v1.5 MySQL conversation sessions and preferences

Revision ID: 003
Revises: 002
Create Date: 2026-09-09
"""

from alembic import op
import sqlalchemy as sa


revision = "003"
down_revision = "002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "chat_sessions",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=120), nullable=False, server_default="新对话"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_active_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_chat_sessions_user_id", "chat_sessions", ["user_id"])
    op.create_index("ix_chat_sessions_last_active_at", "chat_sessions", ["last_active_at"])

    with op.batch_alter_table("chat_history") as batch_op:
        batch_op.add_column(sa.Column("session_id", sa.String(length=36), nullable=True))
        batch_op.create_index("ix_chat_history_session_id", ["session_id"])
        batch_op.create_foreign_key(
            "fk_chat_history_session_id", "chat_sessions", ["session_id"], ["id"], ondelete="SET NULL"
        )

    op.create_table(
        "user_preferences",
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("preferred_crafts", sa.JSON(), nullable=False),
        sa.Column("preferred_profile", sa.String(length=20), nullable=True),
        sa.Column("profile_scores", sa.JSON(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("user_id"),
    )


def downgrade() -> None:
    op.drop_table("user_preferences")
    with op.batch_alter_table("chat_history") as batch_op:
        batch_op.drop_constraint("fk_chat_history_session_id", type_="foreignkey")
        batch_op.drop_index("ix_chat_history_session_id")
        batch_op.drop_column("session_id")
    op.drop_index("ix_chat_sessions_last_active_at", table_name="chat_sessions")
    op.drop_index("ix_chat_sessions_user_id", table_name="chat_sessions")
    op.drop_table("chat_sessions")
