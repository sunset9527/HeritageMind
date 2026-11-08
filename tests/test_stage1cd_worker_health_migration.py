import importlib.util
from datetime import datetime
from pathlib import Path

import sqlalchemy as sa
from alembic.migration import MigrationContext
from alembic.operations import Operations


MIGRATION_PATH = Path(__file__).parents[1] / "migrations" / "versions" / "008_worker_dependency_health.py"


def _migration():
    spec = importlib.util.spec_from_file_location("worker_dependency_health_008", MIGRATION_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def _run(connection, direction: str):
    module = _migration()
    module.op = Operations(MigrationContext.configure(connection))
    getattr(module, direction)()


def test_008_adds_worker_dependency_summary_without_losing_existing_heartbeat():
    engine = sa.create_engine("sqlite://")
    with engine.begin() as connection:
        metadata = sa.MetaData()
        heartbeats = sa.Table(
            "worker_heartbeats",
            metadata,
            sa.Column("worker_id", sa.String(128), primary_key=True),
            sa.Column("version", sa.String(64), nullable=False),
            sa.Column("started_at", sa.DateTime(), nullable=False),
            sa.Column("last_seen_at", sa.DateTime(), nullable=False),
        )
        metadata.create_all(connection)
        connection.execute(
            heartbeats.insert().values(
                worker_id="upload-1",
                version="stage1b",
                started_at=datetime(2026, 10, 1),
                last_seen_at=datetime(2026, 10, 1),
            )
        )

        _run(connection, "upgrade")
        columns = {column["name"] for column in sa.inspect(connection).get_columns("worker_heartbeats")}
        assert {"status", "dependencies_json", "last_error_code"}.issubset(columns)

        row = connection.execute(sa.text("SELECT worker_id, status, dependencies_json, last_error_code FROM worker_heartbeats")).mappings().one()
        assert row == {
            "worker_id": "upload-1",
            "status": "unknown",
            "dependencies_json": "{}",
            "last_error_code": None,
        }

        _run(connection, "downgrade")
        remaining = {column["name"] for column in sa.inspect(connection).get_columns("worker_heartbeats")}
        assert "worker_id" in remaining
        assert "status" not in remaining


def test_worker_heartbeat_persists_only_safe_dependency_codes():
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy.pool import StaticPool

    from src.database import Base
    from src.models.upload import WorkerHeartbeat
    from src.services.task_state import update_worker_heartbeat

    engine = create_engine("sqlite://", poolclass=StaticPool)
    Base.metadata.create_all(engine)
    db = sessionmaker(bind=engine)()
    try:
        update_worker_heartbeat(
            db,
            "worker-1",
            "stage1cd",
            status="degraded",
            dependencies={"redis": {"status": "unavailable", "reason_code": "connection_failed"}},
            last_error_code="connection_failed",
        )
        row = db.get(WorkerHeartbeat, "worker-1")
        assert row.status == "degraded"
        assert row.dependencies_json == '{"redis":{"reason_code":"connection_failed","status":"unavailable"}}'
        assert row.last_error_code == "connection_failed"
    finally:
        db.close()
        engine.dispose()
