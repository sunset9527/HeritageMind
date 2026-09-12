"""add source-backed v2 platform content and graph review tables

Revision ID: 005
Revises: 004
Create Date: 2026-09-12
"""

from alembic import op
import sqlalchemy as sa


revision = "005"
down_revision = "004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "craft_entries",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("slug", sa.String(length=120), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"), sa.UniqueConstraint("name"), sa.UniqueConstraint("slug"),
    )
    op.create_index("ix_craft_entries_name", "craft_entries", ["name"])
    op.create_index("ix_craft_entries_slug", "craft_entries", ["slug"])
    op.create_index("ix_craft_entries_status", "craft_entries", ["status"])
    op.create_table(
        "inheritor_profiles",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("slug", sa.String(length=120), nullable=False),
        sa.Column("craft_name", sa.String(length=100), nullable=False),
        sa.Column("region", sa.String(length=100), nullable=False),
        sa.Column("recognition", sa.String(length=255), nullable=False),
        sa.Column("biography", sa.Text(), nullable=False), sa.Column("lineage", sa.Text(), nullable=False),
        sa.Column("representative_works", sa.Text(), nullable=False), sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False), sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"), sa.UniqueConstraint("name"), sa.UniqueConstraint("slug"),
    )
    for column in ("name", "slug", "craft_name", "status"):
        op.create_index(f"ix_inheritor_profiles_{column}", "inheritor_profiles", [column])
    op.create_table(
        "source_evidence",
        sa.Column("id", sa.Integer(), nullable=False), sa.Column("subject_type", sa.String(length=32), nullable=False),
        sa.Column("subject_id", sa.Integer(), nullable=False), sa.Column("source_url", sa.String(length=500), nullable=False),
        sa.Column("source_name", sa.String(length=255), nullable=False), sa.Column("evidence_text", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False), sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_source_evidence_subject_type", "source_evidence", ["subject_type"])
    op.create_index("ix_source_evidence_subject_id", "source_evidence", ["subject_id"])
    op.create_table(
        "graph_change_candidates",
        sa.Column("id", sa.Integer(), nullable=False), sa.Column("source_entity", sa.String(length=160), nullable=False),
        sa.Column("source_type", sa.String(length=32), nullable=False), sa.Column("relation", sa.String(length=64), nullable=False),
        sa.Column("target_entity", sa.String(length=160), nullable=False), sa.Column("target_type", sa.String(length=32), nullable=False),
        sa.Column("evidence_text", sa.Text(), nullable=False), sa.Column("source_url", sa.String(length=500), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False), sa.Column("reviewed_by_user_id", sa.Integer(), nullable=True),
        sa.Column("review_reason", sa.Text(), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["reviewed_by_user_id"], ["users.id"], ondelete="SET NULL"), sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("source_entity", "relation", "target_entity", "source_url", name="uq_graph_candidate_fact_source"),
    )
    for column in ("source_entity", "target_entity", "status"):
        op.create_index(f"ix_graph_change_candidates_{column}", "graph_change_candidates", [column])
    op.create_table(
        "audit_logs",
        sa.Column("id", sa.Integer(), nullable=False), sa.Column("actor_user_id", sa.Integer(), nullable=True),
        sa.Column("action", sa.String(length=80), nullable=False), sa.Column("subject_type", sa.String(length=32), nullable=False),
        sa.Column("subject_id", sa.Integer(), nullable=False), sa.Column("detail", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["actor_user_id"], ["users.id"], ondelete="SET NULL"), sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_audit_logs_actor_user_id", "audit_logs", ["actor_user_id"])
    op.create_index("ix_audit_logs_action", "audit_logs", ["action"])


def downgrade() -> None:
    op.drop_table("audit_logs")
    op.drop_table("graph_change_candidates")
    op.drop_table("source_evidence")
    op.drop_table("inheritor_profiles")
    op.drop_table("craft_entries")
