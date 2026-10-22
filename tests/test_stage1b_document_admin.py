"""管理员文档草稿的查询、重试和删除状态机。"""

from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from config import settings
from src.database import Base
from src.models.upload import DocumentUpload


def _db():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)(), engine


def _row(db, root: Path, *, status: str = "failed", attempts: int = 1) -> DocumentUpload:
    name = "e" * 32 + ".txt"
    root.mkdir(parents=True, exist_ok=True)
    (root / name).write_text("正文", encoding="utf-8")
    row = DocumentUpload(
        craft_id="suxiu",
        craft_name="苏绣",
        storage_name=name,
        original_name="资料.txt",
        extension=".txt",
        mime_type="text/plain",
        size_bytes=6,
        content_sha256="f" * 64,
        processing_status=status,
        attempts=attempts,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def test_failed_document_can_retry_only_before_attempt_limit(tmp_path):
    from src.services.document_upload import DocumentStateError, retry_document

    db, engine = _db()
    try:
        row = _row(db, tmp_path)
        retried = retry_document(db, row.id, max_attempts=settings.upload_task_max_attempts)
        assert retried.processing_status == "pending"
        assert retried.error_code is None

        retried.processing_status = "failed"
        retried.attempts = settings.upload_task_max_attempts
        db.commit()
        with pytest.raises(DocumentStateError):
            retry_document(db, row.id, max_attempts=settings.upload_task_max_attempts)
    finally:
        db.close()
        engine.dispose()


def test_processing_document_cannot_be_deleted(tmp_path):
    from src.services.document_upload import DocumentStateError, delete_document

    db, engine = _db()
    try:
        row = _row(db, tmp_path, status="processing")
        with pytest.raises(DocumentStateError):
            delete_document(db, row.id, storage_root=tmp_path)
        assert (tmp_path / row.storage_name).exists()
    finally:
        db.close()
        engine.dispose()


def test_deleting_draft_removes_original_and_parsed_artifact(tmp_path):
    from src.services.document_upload import delete_document

    db, engine = _db()
    try:
        row = _row(db, tmp_path, status="failed")
        row.parsed_storage_name = "parsed.txt"
        (tmp_path / "parsed.txt").write_text("解析", encoding="utf-8")
        db.commit()
        row_id = row.id

        assert delete_document(db, row_id, storage_root=tmp_path) is True
        assert db.get(DocumentUpload, row_id) is None
        assert list(tmp_path.iterdir()) == []
    finally:
        db.close()
        engine.dispose()


def test_document_admin_responses_do_not_expose_absolute_paths():
    from src.schemas.upload import DocumentUploadListResponse, DocumentUploadResponse

    assert "storage_path" not in DocumentUploadResponse.model_fields
    assert "absolute_path" not in DocumentUploadResponse.model_fields
    assert "worker_status" in DocumentUploadListResponse.model_fields
