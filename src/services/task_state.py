"""后台任务的数据库原子状态迁移、恢复扫描与 worker 心跳。"""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone

from sqlalchemy import select, update

from src.models.upload import DocumentUpload, ProcessingStatus, WorkerHeartbeat
from src.services.queue import push_job


def utcnow_naive() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _naive(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is not None:
        return value.astimezone(timezone.utc).replace(tzinfo=None)
    return value


def claim_document(db, document_id: int, *, max_attempts: int) -> bool:
    result = db.execute(
        update(DocumentUpload)
        .where(
            DocumentUpload.id == document_id,
            DocumentUpload.processing_status.in_(
                [ProcessingStatus.PENDING.value, ProcessingStatus.FAILED.value]
            ),
            DocumentUpload.attempts < max_attempts,
        )
        .values(
            processing_status=ProcessingStatus.PROCESSING.value,
            attempts=DocumentUpload.attempts + 1,
            started_at=utcnow_naive(),
            finished_at=None,
            error_code=None,
            error_message=None,
        )
        .execution_options(synchronize_session=False)
    )
    db.commit()
    return bool(result.rowcount)


async def sweep_document_jobs(
    db,
    *,
    stale_minutes: int,
    max_attempts: int,
) -> int:
    cutoff = utcnow_naive() - timedelta(minutes=stale_minutes)
    rows = list(
        db.scalars(
            select(DocumentUpload).where(
                DocumentUpload.processing_status.in_(
                    [ProcessingStatus.PENDING.value, ProcessingStatus.PROCESSING.value]
                )
            )
        )
    )
    candidates: list[int] = []
    for row in rows:
        if row.processing_status == ProcessingStatus.PROCESSING.value:
            started_at = _naive(row.started_at)
            if started_at is not None and started_at > cutoff:
                continue
            if row.attempts >= max_attempts:
                row.processing_status = ProcessingStatus.FAILED.value
                row.error_code = "attempts_exhausted"
                row.error_message = "worker sweep: 处理超时且达到最大尝试次数"
                row.finished_at = utcnow_naive()
                continue
            row.processing_status = ProcessingStatus.PENDING.value
            row.started_at = None
        elif row.attempts >= max_attempts:
            row.processing_status = ProcessingStatus.FAILED.value
            row.error_code = "attempts_exhausted"
            row.error_message = "worker sweep: 达到最大尝试次数"
            row.finished_at = utcnow_naive()
            continue
        candidates.append(row.id)
    db.commit()

    pushed = 0
    for document_id in candidates:
        if await push_job("document", document_id):
            pushed += 1
    return pushed


def _safe_dependency_summary(dependencies: dict | None) -> str:
    safe: dict[str, dict[str, str | None]] = {}
    for name, value in (dependencies or {}).items():
        if not isinstance(value, dict):
            continue
        status = value.get("status")
        reason_code = value.get("reason_code")
        if isinstance(status, str):
            safe[str(name)] = {
                "status": status[:20],
                "reason_code": reason_code[:80] if isinstance(reason_code, str) else None,
            }
    return json.dumps(safe, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def update_worker_heartbeat(
    db,
    worker_id: str,
    version: str,
    *,
    status: str = "unknown",
    dependencies: dict | None = None,
    last_error_code: str | None = None,
) -> WorkerHeartbeat:
    now = utcnow_naive()
    row = db.get(WorkerHeartbeat, worker_id)
    if row is None:
        row = WorkerHeartbeat(
            worker_id=worker_id,
            version=version,
            started_at=now,
            last_seen_at=now,
            status=status,
            dependencies_json=_safe_dependency_summary(dependencies),
            last_error_code=last_error_code[:80] if last_error_code else None,
        )
        db.add(row)
    else:
        row.version = version
        row.last_seen_at = now
        row.status = status
        row.dependencies_json = _safe_dependency_summary(dependencies)
        row.last_error_code = last_error_code[:80] if last_error_code else None
    db.commit()
    return row


def worker_health(db, *, stale_seconds: int = 60) -> str:
    latest = db.scalar(
        select(WorkerHeartbeat).order_by(WorkerHeartbeat.last_seen_at.desc()).limit(1)
    )
    if latest is None:
        return "offline"
    seen = _naive(latest.last_seen_at)
    if seen is None or seen < utcnow_naive() - timedelta(seconds=stale_seconds):
        return "stale"
    return "online"
