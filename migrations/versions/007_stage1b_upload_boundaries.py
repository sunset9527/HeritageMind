"""add bounded upload resources, maintenance jobs and worker heartbeats

Revision ID: 007
Revises: 006
Create Date: 2026-10-21

This migration also bridges databases that created the historic media tables
through ``Base.metadata.create_all()``.  A small provenance table records which
legacy tables predated this migration so downgrade never deletes user data.
"""

from alembic import op
import sqlalchemy as sa


revision = "007"
down_revision = "006"
branch_labels = None
depends_on = None


_STATE_TABLE = "_stage1b_migration_state"
_CRAFT_IDS = {
    "景泰蓝": "jingtailan",
    "苏绣": "suxiu",
    "龙泉青瓷": "longquan_ci",
    "宜兴紫砂": "yixing_zisha",
    "芜湖铁画": "wuhu_tiehua",
    "蜀锦": "shujin",
    "剪纸": "jianzhi",
    "景德镇瓷器": "jingdezhen_ciqi",
    "南京云锦": "nanjing_yunjin",
    "东阳木雕": "dongyang_mudiao",
    "苗族蜡染": "miaozu_laran",
    "木版年画": "muban_nianhua",
    "缂丝": "kesi",
    "竹编": "zhubian",
    "玉雕": "yudiao",
    "漆器": "qiqi",
    "唐三彩": "tangsancai",
    "钧瓷": "junci",
    "汝瓷": "ruci",
    "泥人张": "nirenzhang",
    "皮影戏": "piyingxi",
    "壮锦": "zhuangjin",
    "京剧": "jingju",
}


def _inspector():
    return sa.inspect(op.get_bind())


def _has_table(name: str) -> bool:
    return name in _inspector().get_table_names()


def _column_names(table: str) -> set[str]:
    return {column["name"] for column in _inspector().get_columns(table)}


def _index_names(table: str) -> set[str]:
    return {index["name"] for index in _inspector().get_indexes(table)}


def _create_index_if_missing(name: str, table: str, columns: list[str]) -> None:
    if name not in _index_names(table):
        op.create_index(name, table, columns)


def _drop_index_if_present(name: str, table: str) -> None:
    if name in _index_names(table):
        op.drop_index(name, table_name=table)


def _create_state_table() -> None:
    if not _has_table(_STATE_TABLE):
        op.create_table(
            _STATE_TABLE,
            sa.Column("resource", sa.String(length=80), primary_key=True),
            sa.Column("existed_before", sa.Boolean(), nullable=False),
        )


def _record_original_table(resource: str, existed_before: bool) -> None:
    bind = op.get_bind()
    existing = bind.execute(
        sa.text(f"SELECT resource FROM {_STATE_TABLE} WHERE resource = :resource"),
        {"resource": resource},
    ).first()
    if existing is None:
        bind.execute(
            sa.text(
                f"INSERT INTO {_STATE_TABLE} (resource, existed_before) "
                "VALUES (:resource, :existed_before)"
            ),
            {"resource": resource, "existed_before": existed_before},
        )


def _existed_before(resource: str) -> bool:
    if not _has_table(_STATE_TABLE):
        return False
    value = op.get_bind().execute(
        sa.text(f"SELECT existed_before FROM {_STATE_TABLE} WHERE resource = :resource"),
        {"resource": resource},
    ).scalar_one_or_none()
    return bool(value)


def _create_media_documents() -> None:
    op.create_table(
        "media_documents",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("craft_id", sa.String(length=120), nullable=True),
        sa.Column("craft_name", sa.String(length=100), nullable=False),
        sa.Column("media_type", sa.String(length=20), nullable=False),
        sa.Column("filename", sa.String(length=255), nullable=False),
        sa.Column("original_name", sa.String(length=255), nullable=False),
        sa.Column("mime_type", sa.String(length=50), nullable=False),
        sa.Column("size", sa.Integer(), nullable=False),
        sa.Column("content_sha256", sa.String(length=64), nullable=True),
        sa.Column("uploaded_by_user_id", sa.Integer(), nullable=True),
        sa.Column("title", sa.String(length=255), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["uploaded_by_user_id"], ["users.id"], ondelete="SET NULL"
        ),
    )


def _upgrade_media_documents() -> None:
    if not _has_table("media_documents"):
        _create_media_documents()
    else:
        columns = _column_names("media_documents")
        with op.batch_alter_table("media_documents") as batch_op:
            if "craft_id" not in columns:
                batch_op.add_column(sa.Column("craft_id", sa.String(length=120), nullable=True))
            if "content_sha256" not in columns:
                batch_op.add_column(
                    sa.Column("content_sha256", sa.String(length=64), nullable=True)
                )
            if "uploaded_by_user_id" not in columns:
                batch_op.add_column(
                    sa.Column("uploaded_by_user_id", sa.Integer(), nullable=True)
                )
                batch_op.create_foreign_key(
                    "fk_media_documents_uploaded_by_user_id_users",
                    "users",
                    ["uploaded_by_user_id"],
                    ["id"],
                    ondelete="SET NULL",
                )

    _create_index_if_missing("ix_media_documents_craft_id", "media_documents", ["craft_id"])
    _create_index_if_missing(
        "ix_media_documents_content_sha256", "media_documents", ["content_sha256"]
    )
    _create_index_if_missing(
        "ix_media_documents_uploaded_by_user_id",
        "media_documents",
        ["uploaded_by_user_id"],
    )
    _create_index_if_missing(
        "ix_media_documents_craft_name", "media_documents", ["craft_name"]
    )

    bind = op.get_bind()
    for craft_name, craft_id in _CRAFT_IDS.items():
        bind.execute(
            sa.text(
                "UPDATE media_documents SET craft_id = :craft_id "
                "WHERE craft_id IS NULL AND craft_name = :craft_name"
            ),
            {"craft_id": craft_id, "craft_name": craft_name},
        )


def _create_audio_transcripts() -> None:
    op.create_table(
        "audio_transcripts",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("media_id", sa.Integer(), nullable=False),
        sa.Column("craft_name", sa.String(length=100), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False),
        sa.Column("language", sa.String(length=20), nullable=True),
        sa.Column("duration_ms", sa.Integer(), nullable=True),
        sa.Column("full_text", sa.Text(), nullable=True),
        sa.Column("chunk_count", sa.Integer(), nullable=False),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["media_id"], ["media_documents.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("media_id", name="uq_audio_transcripts_media_id"),
    )
    _create_index_if_missing(
        "ix_audio_transcripts_craft_name", "audio_transcripts", ["craft_name"]
    )
    _create_index_if_missing(
        "ix_audio_transcripts_status", "audio_transcripts", ["status"]
    )


def _create_document_uploads() -> None:
    op.create_table(
        "document_uploads",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("uploaded_by_user_id", sa.Integer(), nullable=True),
        sa.Column("craft_id", sa.String(length=120), nullable=False),
        sa.Column("craft_name", sa.String(length=100), nullable=False),
        sa.Column("storage_name", sa.String(length=255), nullable=False, unique=True),
        sa.Column("original_name", sa.String(length=255), nullable=False),
        sa.Column("extension", sa.String(length=16), nullable=False),
        sa.Column("mime_type", sa.String(length=100), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("content_sha256", sa.String(length=64), nullable=False),
        sa.Column("parsed_storage_name", sa.String(length=255), nullable=True),
        sa.Column("char_count", sa.Integer(), nullable=False),
        sa.Column("page_count", sa.Integer(), nullable=False),
        sa.Column("ocr_page_count", sa.Integer(), nullable=False),
        sa.Column("review_status", sa.String(length=20), nullable=False),
        sa.Column("processing_status", sa.String(length=20), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False),
        sa.Column("error_code", sa.String(length=80), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["uploaded_by_user_id"], ["users.id"], ondelete="SET NULL"
        ),
    )
    for column in (
        "uploaded_by_user_id",
        "craft_id",
        "craft_name",
        "content_sha256",
        "review_status",
        "processing_status",
    ):
        op.create_index(f"ix_document_uploads_{column}", "document_uploads", [column])


def _create_maintenance_jobs() -> None:
    op.create_table(
        "maintenance_jobs",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("kind", sa.String(length=40), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False),
        sa.Column("input_count", sa.Integer(), nullable=False),
        sa.Column("input_chars", sa.Integer(), nullable=False),
        sa.Column("output_version", sa.String(length=120), nullable=True),
        sa.Column("error_code", sa.String(length=80), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_maintenance_jobs_kind", "maintenance_jobs", ["kind"])
    op.create_index("ix_maintenance_jobs_status", "maintenance_jobs", ["status"])


def _create_worker_heartbeats() -> None:
    op.create_table(
        "worker_heartbeats",
        sa.Column("worker_id", sa.String(length=128), primary_key=True),
        sa.Column("version", sa.String(length=64), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False),
    )


def upgrade() -> None:
    media_existed = _has_table("media_documents")
    audio_existed = _has_table("audio_transcripts")
    _create_state_table()
    _record_original_table("media_documents", media_existed)
    _record_original_table("audio_transcripts", audio_existed)

    _upgrade_media_documents()
    if not audio_existed:
        _create_audio_transcripts()
    if not _has_table("document_uploads"):
        _create_document_uploads()
    if not _has_table("maintenance_jobs"):
        _create_maintenance_jobs()
    if not _has_table("worker_heartbeats"):
        _create_worker_heartbeats()


def _remove_added_media_columns() -> None:
    for index in (
        "ix_media_documents_uploaded_by_user_id",
        "ix_media_documents_content_sha256",
        "ix_media_documents_craft_id",
    ):
        _drop_index_if_present(index, "media_documents")
    columns = _column_names("media_documents")
    with op.batch_alter_table("media_documents") as batch_op:
        for column in ("uploaded_by_user_id", "content_sha256", "craft_id"):
            if column in columns:
                batch_op.drop_column(column)


def downgrade() -> None:
    media_existed = _existed_before("media_documents")
    audio_existed = _existed_before("audio_transcripts")

    for table in ("worker_heartbeats", "maintenance_jobs", "document_uploads"):
        if _has_table(table):
            op.drop_table(table)

    if _has_table("audio_transcripts") and not audio_existed:
        op.drop_table("audio_transcripts")
    if _has_table("media_documents"):
        if media_existed:
            _remove_added_media_columns()
        else:
            op.drop_table("media_documents")
    if _has_table(_STATE_TABLE):
        op.drop_table(_STATE_TABLE)
