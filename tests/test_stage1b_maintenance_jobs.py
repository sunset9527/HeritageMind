"""三类索引重建只创建可去重的后台维护任务。"""

import pytest
from datetime import datetime, timedelta, timezone
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.database import Base
from src.models.upload import MaintenanceJob, MaintenanceJobKind


def _db():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)(), engine


def test_same_kind_pending_or_processing_job_is_rejected():
    from src.services.maintenance_jobs import MaintenanceConflict, create_maintenance_job

    db, engine = _db()
    try:
        first = create_maintenance_job(db, MaintenanceJobKind.KNOWLEDGE_INDEX.value)
        assert first.status == "pending"
        with pytest.raises(MaintenanceConflict):
            create_maintenance_job(db, MaintenanceJobKind.KNOWLEDGE_INDEX.value)

        second = create_maintenance_job(db, MaintenanceJobKind.IMAGE_INDEX.value)
        assert second.id != first.id
    finally:
        db.close()
        engine.dispose()


@pytest.mark.parametrize(
    ("path", "method"),
    [
        ("/knowledge/rebuild-embeddings", "POST"),
        ("/search/index-images", "POST"),
        ("/search/audio/index", "POST"),
    ],
)
def test_index_rebuild_routes_return_202_without_inline_rebuild(path, method):
    from api import app

    route = next(
        route
        for route in app.routes
        if getattr(route, "path", None) == path and method in route.methods
    )
    assert route.status_code == 202


def test_claim_maintenance_job_is_atomic():
    from src.services.maintenance_jobs import claim_maintenance_job, create_maintenance_job

    db, engine = _db()
    try:
        row = create_maintenance_job(db, MaintenanceJobKind.AUDIO_INDEX.value)
        assert claim_maintenance_job(db, row.id, max_attempts=3) is True
        assert claim_maintenance_job(db, row.id, max_attempts=3) is False
        db.refresh(row)
        assert row.status == "processing"
        assert row.attempts == 1
    finally:
        db.close()
        engine.dispose()


@pytest.mark.asyncio
async def test_processing_job_records_real_builder_stats(monkeypatch):
    import src.services.maintenance_jobs as service
    from src.services.maintenance_jobs import create_maintenance_job, process_maintenance_job

    db, engine = _db()
    try:
        row = create_maintenance_job(db, MaintenanceJobKind.KNOWLEDGE_INDEX.value)
        monkeypatch.setattr(
            service,
            "build_job_snapshot",
            lambda _db, _row: ("version-1", {"input_count": 23, "input_chars": 456}),
        )

        assert await process_maintenance_job(row.id, db=db) == "ready"
        db.refresh(row)
        assert row.output_version == "version-1"
        assert row.input_count == 23
        assert row.input_chars == 456
        assert row.status == "ready"
    finally:
        db.close()
        engine.dispose()


@pytest.mark.asyncio
async def test_sweep_requeues_pending_and_stale_maintenance_jobs(monkeypatch):
    from config import settings
    from src.services import queue
    from src.services.maintenance_jobs import create_maintenance_job, sweep_maintenance_jobs
    from tests.redis_stub import StubRedis

    db, engine = _db()
    stub = StubRedis()
    monkeypatch.setattr(queue, "_redis", stub)
    try:
        pending = create_maintenance_job(db, MaintenanceJobKind.KNOWLEDGE_INDEX.value)
        stale = create_maintenance_job(db, MaintenanceJobKind.IMAGE_INDEX.value)
        stale.status = "processing"
        stale.attempts = 1
        stale.started_at = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(minutes=30)
        db.commit()

        assert await sweep_maintenance_jobs(db, stale_minutes=15, max_attempts=3) == 2
        db.refresh(stale)
        assert stale.status == "pending"
        assert len(stub.lists[settings.task_queue_key]) == 2
        assert pending.id != stale.id
    finally:
        db.close()
        engine.dispose()
