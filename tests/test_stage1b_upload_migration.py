"""007 迁移同时兼容空库和历史 create_all 库。"""

import importlib.util
from pathlib import Path

import sqlalchemy as sa
from alembic.migration import MigrationContext
from alembic.operations import Operations


MIGRATION_PATH = Path(__file__).parents[1] / "migrations" / "versions" / "007_stage1b_upload_boundaries.py"


def _load_migration():
    spec = importlib.util.spec_from_file_location("stage1b_migration_007", MIGRATION_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def _run(connection, direction: str):
    module = _load_migration()
    module.op = Operations(MigrationContext.configure(connection))
    getattr(module, direction)()


def _create_users(connection):
    metadata = sa.MetaData()
    sa.Table(
        "users",
        metadata,
        sa.Column("id", sa.Integer(), primary_key=True),
    )
    metadata.create_all(connection)


def _create_legacy_media_tables(connection):
    metadata = sa.MetaData()
    sa.Table(
        "media_documents",
        metadata,
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("craft_name", sa.String(100), nullable=False),
        sa.Column("media_type", sa.String(20), nullable=False),
        sa.Column("filename", sa.String(255), nullable=False),
        sa.Column("original_name", sa.String(255), nullable=False),
        sa.Column("mime_type", sa.String(50), nullable=False),
        sa.Column("size", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(255)),
        sa.Column("status", sa.String(20)),
        sa.Column("created_at", sa.DateTime(timezone=True)),
    )
    sa.Table(
        "audio_transcripts",
        metadata,
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("media_id", sa.Integer(), nullable=False, unique=True),
        sa.Column("craft_name", sa.String(100), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False),
    )
    metadata.create_all(connection)


def test_007_upgrade_creates_upload_tables_on_clean_database():
    engine = sa.create_engine("sqlite://")
    with engine.begin() as connection:
        _create_users(connection)
        _run(connection, "upgrade")
        tables = set(sa.inspect(connection).get_table_names())

        assert {
            "media_documents",
            "audio_transcripts",
            "document_uploads",
            "maintenance_jobs",
            "worker_heartbeats",
        }.issubset(tables)
        media_columns = {column["name"] for column in sa.inspect(connection).get_columns("media_documents")}
        assert {"craft_id", "content_sha256", "uploaded_by_user_id"}.issubset(media_columns)


def test_007_upgrade_preserves_legacy_media_and_backfills_known_craft_id():
    engine = sa.create_engine("sqlite://")
    with engine.begin() as connection:
        _create_users(connection)
        _create_legacy_media_tables(connection)
        connection.execute(sa.text(
            "INSERT INTO media_documents "
            "(id, craft_name, media_type, filename, original_name, mime_type, size, title, status) "
            "VALUES (1, '景泰蓝', 'IMAGE', 'old.jpg', 'old.jpg', 'image/jpeg', 3, '', 'draft')"
        ))

        _run(connection, "upgrade")

        row = connection.execute(sa.text(
            "SELECT craft_name, craft_id, filename FROM media_documents WHERE id = 1"
        )).mappings().one()
        assert row == {"craft_name": "景泰蓝", "craft_id": "jingtailan", "filename": "old.jpg"}


def test_007_downgrade_preserves_preexisting_media_table_and_rows():
    engine = sa.create_engine("sqlite://")
    with engine.begin() as connection:
        _create_users(connection)
        _create_legacy_media_tables(connection)
        connection.execute(sa.text(
            "INSERT INTO media_documents "
            "(id, craft_name, media_type, filename, original_name, mime_type, size, title, status) "
            "VALUES (1, '未知旧技艺', 'IMAGE', 'old.jpg', 'old.jpg', 'image/jpeg', 3, '', 'draft')"
        ))
        _run(connection, "upgrade")

        _run(connection, "downgrade")

        tables = set(sa.inspect(connection).get_table_names())
        assert "media_documents" in tables
        assert "audio_transcripts" in tables
        assert "document_uploads" not in tables
        assert connection.execute(sa.text("SELECT COUNT(*) FROM media_documents")).scalar_one() == 1
        media_columns = {column["name"] for column in sa.inspect(connection).get_columns("media_documents")}
        assert "craft_id" not in media_columns
