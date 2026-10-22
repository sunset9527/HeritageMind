"""阶段 1B 上传、维护任务和 worker 心跳模型。"""

from datetime import datetime, timezone

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.database import Base
from src.models.media import MediaDocument


def _session():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)(), engine


def test_media_document_has_stage1b_audit_columns():
    columns = MediaDocument.__table__.columns

    assert columns["craft_id"].nullable is True
    assert columns["content_sha256"].nullable is True
    assert columns["uploaded_by_user_id"].nullable is True


def test_document_upload_keeps_review_and_processing_states_separate():
    from src.models.upload import DocumentProcessingStatus, DocumentUpload, ReviewStatus

    db, engine = _session()
    try:
        row = DocumentUpload(
            craft_id="jingtailan",
            craft_name="景泰蓝",
            storage_name="abc.pdf",
            original_name="资料.pdf",
            extension=".pdf",
            mime_type="application/pdf",
            size_bytes=123,
            content_sha256="a" * 64,
        )
        db.add(row)
        db.commit()
        db.refresh(row)

        assert row.review_status == ReviewStatus.DRAFT.value
        assert row.processing_status == DocumentProcessingStatus.PENDING.value
        assert row.attempts == 0
        assert row.parsed_storage_name is None
    finally:
        db.close()
        engine.dispose()

def test_maintenance_job_supports_all_three_index_kinds():
    from src.models.upload import MaintenanceJob, MaintenanceJobKind, ProcessingStatus

    db, engine = _session()
    try:
        for kind in (
            MaintenanceJobKind.KNOWLEDGE_INDEX,
            MaintenanceJobKind.IMAGE_INDEX,
            MaintenanceJobKind.AUDIO_INDEX,
        ):
            db.add(MaintenanceJob(kind=kind.value))
        db.commit()

        rows = db.query(MaintenanceJob).order_by(MaintenanceJob.id).all()
        assert [row.kind for row in rows] == [kind.value for kind in MaintenanceJobKind]
        assert {row.status for row in rows} == {ProcessingStatus.PENDING.value}
    finally:
        db.close()
        engine.dispose()


def test_worker_heartbeat_is_unique_per_worker_id_and_tracks_last_seen():
    from src.models.upload import WorkerHeartbeat

    db, engine = _session()
    try:
        now = datetime.now(timezone.utc)
        row = WorkerHeartbeat(worker_id="upload-worker-1", version="stage1b", last_seen_at=now)
        db.add(row)
        db.commit()

        persisted = db.get(WorkerHeartbeat, "upload-worker-1")
        assert persisted.version == "stage1b"
        assert persisted.last_seen_at is not None
    finally:
        db.close()
        engine.dispose()
