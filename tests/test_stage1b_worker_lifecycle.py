"""独立上传 worker 的原子抢占、恢复扫描和心跳。"""

import asyncio
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from config import settings
from src.database import Base
from src.models.upload import DocumentUpload, WorkerHeartbeat
from src.services import queue
from tests.redis_stub import StubRedis


def _db():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)(), engine


def _document(db, *, status="pending", attempts=0, started_at=None):
    row = DocumentUpload(
        craft_id="jingtailan",
        craft_name="景泰蓝",
        storage_name=f"{uuid4().hex}.txt",
        original_name="资料.txt",
        extension=".txt",
        mime_type="text/plain",
        size_bytes=3,
        content_sha256="a" * 64,
        processing_status=status,
        attempts=attempts,
        started_at=started_at,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def test_document_claim_is_compare_and_swap():
    from src.services.task_state import claim_document

    db, engine = _db()
    try:
        row = _document(db)
        assert claim_document(db, row.id, max_attempts=3) is True
        assert claim_document(db, row.id, max_attempts=3) is False
        db.refresh(row)
        assert row.processing_status == "processing"
        assert row.attempts == 1
    finally:
        db.close()
        engine.dispose()


def test_sweep_requeues_pending_and_stale_but_not_recent(monkeypatch):
    from src.services.task_state import sweep_document_jobs

    db, engine = _db()
    stub = StubRedis()
    monkeypatch.setattr(queue, "_redis", stub)
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    try:
        pending = _document(db)
        stale = _document(db, status="processing", attempts=1, started_at=now - timedelta(minutes=30))
        recent = _document(db, status="processing", attempts=1, started_at=now)

        pushed = asyncio.run(
            sweep_document_jobs(db, stale_minutes=15, max_attempts=3)
        )

        assert pushed == 2
        db.refresh(stale)
        db.refresh(recent)
        assert stale.processing_status == "pending"
        assert recent.processing_status == "processing"
        assert len(stub.lists[settings.task_queue_key]) == 2
        assert pending.id != stale.id
    finally:
        db.close()
        engine.dispose()


def test_heartbeat_upsert_does_not_create_duplicate_rows():
    from src.services.task_state import update_worker_heartbeat, worker_health

    db, engine = _db()
    try:
        update_worker_heartbeat(db, "worker-1", "stage1b")
        update_worker_heartbeat(db, "worker-1", "stage1b-next")

        assert db.query(WorkerHeartbeat).count() == 1
        assert db.get(WorkerHeartbeat, "worker-1").version == "stage1b-next"
        assert worker_health(db, stale_seconds=60) == "online"
        db.get(WorkerHeartbeat, "worker-1").last_seen_at = (
            datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(minutes=5)
        )
        db.commit()
        assert worker_health(db, stale_seconds=60) == "stale"
    finally:
        db.close()
        engine.dispose()


def test_api_lifespan_has_no_embedded_upload_consumer():
    import api

    assert not hasattr(api, "_worker_task")
    assert not hasattr(api, "_worker_stop")
