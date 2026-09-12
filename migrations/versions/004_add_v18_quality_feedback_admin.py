"""add v1.8 quality evaluation, feedback and safe Agent configuration

Revision ID: 004
Revises: 003
Create Date: 2026-09-12
"""

from alembic import op
import sqlalchemy as sa


revision = "004"
down_revision = "003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "answer_evaluations",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("chat_id", sa.Integer(), nullable=False),
        sa.Column("total_score", sa.Integer(), nullable=False),
        sa.Column("rule_version", sa.String(length=32), nullable=False),
        sa.Column("score_details", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["chat_id"], ["chat_history.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("chat_id"),
    )
    op.create_index("ix_answer_evaluations_chat_id", "answer_evaluations", ["chat_id"])
    op.create_table(
        "user_feedback",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("chat_id", sa.Integer(), nullable=False),
        sa.Column("sentiment", sa.String(length=8), nullable=False),
        sa.Column("comment", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["chat_id"], ["chat_history.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "chat_id", name="uq_feedback_user_chat"),
    )
    op.create_index("ix_user_feedback_user_id", "user_feedback", ["user_id"])
    op.create_index("ix_user_feedback_chat_id", "user_feedback", ["chat_id"])
    op.create_table(
        "agent_configurations",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("agent_id", sa.String(length=64), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("display_name", sa.String(length=80), nullable=True),
        sa.Column("capability", sa.String(length=255), nullable=True),
        sa.Column("collaboration_priority", sa.Integer(), nullable=False, server_default="100"),
        sa.Column("parameters", sa.JSON(), nullable=False),
        sa.Column("updated_by_user_id", sa.Integer(), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["updated_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("agent_id"),
    )
    op.create_index("ix_agent_configurations_agent_id", "agent_configurations", ["agent_id"])


def downgrade() -> None:
    op.drop_index("ix_agent_configurations_agent_id", table_name="agent_configurations")
    op.drop_table("agent_configurations")
    op.drop_index("ix_user_feedback_chat_id", table_name="user_feedback")
    op.drop_index("ix_user_feedback_user_id", table_name="user_feedback")
    op.drop_table("user_feedback")
    op.drop_index("ix_answer_evaluations_chat_id", table_name="answer_evaluations")
    op.drop_table("answer_evaluations")
