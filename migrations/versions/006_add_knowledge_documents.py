"""add versioned curated knowledge documents and ingestion runs

Revision ID: 006
Revises: 005
Create Date: 2026-09-14
"""

from alembic import op
import sqlalchemy as sa


revision = "006"
down_revision = "005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "knowledge_documents",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("craft_entry_id", sa.Integer(), nullable=False),
        sa.Column("document_key", sa.String(length=160), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("content_sha256", sa.String(length=64), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("is_current", sa.Boolean(), nullable=False),
        sa.Column("source_name", sa.String(length=255), nullable=False),
        sa.Column("source_url", sa.String(length=500), nullable=False),
        sa.Column("accessed_at", sa.String(length=10), nullable=False),
        sa.Column("license_note", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["craft_entry_id"], ["craft_entries.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("document_key", "version", name="uq_knowledge_document_key_version"),
    )
    for column in ("craft_entry_id", "document_key", "content_sha256", "status", "is_current"):
        op.create_index(f"ix_knowledge_documents_{column}", "knowledge_documents", [column])

    op.create_table(
        "knowledge_ingest_runs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("dataset_version", sa.String(length=80), nullable=False),
        sa.Column("created_count", sa.Integer(), nullable=False),
        sa.Column("updated_count", sa.Integer(), nullable=False),
        sa.Column("skipped_count", sa.Integer(), nullable=False),
        sa.Column("failed_count", sa.Integer(), nullable=False),
        sa.Column("error_summary", sa.Text(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_knowledge_ingest_runs_dataset_version", "knowledge_ingest_runs", ["dataset_version"])


def downgrade() -> None:
    op.drop_table("knowledge_ingest_runs")
    op.drop_table("knowledge_documents")
