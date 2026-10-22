"""隔离文档草稿的持久化与管理员生命周期操作。"""

from __future__ import annotations

import json
import os
from pathlib import Path
from uuid import uuid4

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from src.models.platform import AuditLog
from src.models.upload import DocumentUpload, ProcessingStatus, ReviewStatus
from src.services.upload_security import StagedUpload, resolve_under


class DocumentStateError(ValueError):
    def __init__(self, code: str, detail: str, status_code: int = 409):
        super().__init__(detail)
        self.code = code
        self.detail = detail
        self.status_code = status_code


def persist_staged_document(
    db: Session,
    *,
    staged: StagedUpload,
    storage_root: Path | str,
    craft_id: str,
    craft_name: str,
    uploaded_by_user_id: int | None,
) -> DocumentUpload:
    """把已验证的 ``.part`` 原子发布为待处理草稿。"""
    root = Path(storage_root)
    root.mkdir(parents=True, exist_ok=True)
    final_path = resolve_under(root, staged.storage_name)
    published = False
    row = DocumentUpload(
        uploaded_by_user_id=uploaded_by_user_id,
        craft_id=craft_id,
        craft_name=craft_name,
        storage_name=staged.storage_name,
        original_name=staged.original_name,
        extension=staged.extension,
        mime_type=staged.mime_type,
        size_bytes=staged.size_bytes,
        content_sha256=staged.content_sha256,
        review_status=ReviewStatus.DRAFT.value,
        processing_status=ProcessingStatus.PENDING.value,
        attempts=0,
    )
    try:
        db.add(row)
        db.flush()
        db.add(
            AuditLog(
                actor_user_id=uploaded_by_user_id,
                action="document.uploaded",
                subject_type="document_upload",
                subject_id=row.id,
                detail=json.dumps(
                    {
                        "craft_id": craft_id,
                        "format": staged.format,
                        "size_bytes": staged.size_bytes,
                        "sha256": staged.content_sha256,
                    },
                    ensure_ascii=False,
                ),
            )
        )
        db.flush()
        os.replace(staged.temp_path, final_path)
        published = True
        db.commit()
        db.refresh(row)
        return row
    except Exception:
        db.rollback()
        (final_path if published else staged.temp_path).unlink(missing_ok=True)
        raise


def list_documents(db: Session, *, limit: int = 50, offset: int = 0) -> tuple[list[DocumentUpload], int]:
    total = db.scalar(select(func.count()).select_from(DocumentUpload)) or 0
    rows = list(
        db.scalars(
            select(DocumentUpload)
            .order_by(DocumentUpload.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
    )
    return rows, total


def get_document(db: Session, document_id: int) -> DocumentUpload | None:
    return db.get(DocumentUpload, document_id)


def retry_document(
    db: Session,
    document_id: int,
    *,
    max_attempts: int,
    actor_user_id: int | None = None,
) -> DocumentUpload:
    row = get_document(db, document_id)
    if row is None:
        raise DocumentStateError("not_found", "文档不存在", 404)
    if row.processing_status != ProcessingStatus.FAILED.value:
        raise DocumentStateError("invalid_state", "只有处理失败的文档可以重试")
    if row.attempts >= max_attempts:
        raise DocumentStateError("attempts_exhausted", "文档已达到最大尝试次数")
    row.processing_status = ProcessingStatus.PENDING.value
    row.error_code = None
    row.error_message = None
    row.started_at = None
    row.finished_at = None
    db.add(
        AuditLog(
            actor_user_id=actor_user_id,
            action="document.retry_requested",
            subject_type="document_upload",
            subject_id=row.id,
            detail="",
        )
    )
    db.commit()
    db.refresh(row)
    return row


def delete_document(
    db: Session,
    document_id: int,
    *,
    storage_root: Path | str,
    actor_user_id: int | None = None,
) -> bool:
    row = get_document(db, document_id)
    if row is None:
        return False
    if row.processing_status == ProcessingStatus.PROCESSING.value:
        raise DocumentStateError("processing", "处理中的文档不能删除")

    root = Path(storage_root)
    originals = [resolve_under(root, row.storage_name)]
    if row.parsed_storage_name:
        originals.append(resolve_under(root, row.parsed_storage_name))
    moved: list[tuple[Path, Path]] = []
    try:
        for original in originals:
            if original.exists():
                tombstone = resolve_under(root, f".{uuid4().hex}.delete")
                os.replace(original, tombstone)
                moved.append((original, tombstone))
        db.delete(row)
        db.add(
            AuditLog(
                actor_user_id=actor_user_id,
                action="document.deleted",
                subject_type="document_upload",
                subject_id=document_id,
                detail="",
            )
        )
        db.commit()
    except Exception:
        db.rollback()
        for original, tombstone in reversed(moved):
            if tombstone.exists():
                os.replace(tombstone, original)
        raise
    for _, tombstone in moved:
        tombstone.unlink(missing_ok=True)
    return True
