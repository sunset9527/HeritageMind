"""版本化索引维护任务的创建、去重与原子抢占。"""

from __future__ import annotations

import asyncio
from datetime import timedelta

from sqlalchemy import select, update

from config import settings
from src.models.upload import (
    MaintenanceJob,
    MaintenanceJobKind,
    ProcessingStatus,
)
from src.services.task_state import utcnow_naive


class MaintenanceConflict(ValueError):
    pass


_KINDS = {kind.value for kind in MaintenanceJobKind}


def build_job_snapshot(db, row: MaintenanceJob) -> tuple[str, dict[str, int]]:
    """读取数据库输入并构建相应的真实版本化索引。"""
    from src.models.audio_transcript import AudioTranscript, AudioTranscriptStatus
    from src.models.media import MediaDocument, MediaType
    from src.retrieval.index_snapshot import publish_snapshot
    from src.services.index_builders import (
        build_audio_snapshot,
        build_image_snapshot,
        build_knowledge_snapshot,
    )

    stats: dict[str, int] = {}

    def builder(directory):
        nonlocal stats
        if row.kind == MaintenanceJobKind.KNOWLEDGE_INDEX.value:
            stats = build_knowledge_snapshot(
                directory,
                max_documents=settings.index_max_documents,
                max_total_chars=settings.index_max_total_chars,
            )
            return
        if row.kind == MaintenanceJobKind.IMAGE_INDEX.value:
            media = list(
                db.scalars(
                    select(MediaDocument).where(
                        MediaDocument.media_type == MediaType.IMAGE,
                        MediaDocument.status == "published",
                    )
                )
            )
            stats = build_image_snapshot(
                directory,
                documents=media,
                storage_root=settings.media_storage_path,
                max_documents=settings.index_max_documents,
                max_total_chars=settings.index_max_total_chars,
            )
            return
        if row.kind == MaintenanceJobKind.AUDIO_INDEX.value:
            transcripts = list(
                db.scalars(
                    select(AudioTranscript).where(
                        AudioTranscript.status == AudioTranscriptStatus.INDEXED.value,
                        AudioTranscript.full_text.is_not(None),
                    )
                )
            )
            media_ids = [item.media_id for item in transcripts]
            media = (
                list(db.scalars(select(MediaDocument).where(MediaDocument.id.in_(media_ids))))
                if media_ids
                else []
            )
            from src.retrieval.audio_store import AudioVectorStore

            version = directory.name.removesuffix(".part")
            store = AudioVectorStore(
                collection_name=f"{settings.audio_index_collection}_{version}"
            )
            stats = build_audio_snapshot(
                directory,
                transcripts=transcripts,
                media_by_id={item.id: item for item in media},
                store=store,
                max_documents=settings.index_max_documents,
                max_total_chars=settings.index_max_total_chars,
            )
            return
        raise ValueError(f"未知维护任务类型: {row.kind}")

    version = publish_snapshot(settings.index_versions_path, row.kind, builder)
    return version, stats


def build_maintenance_snapshot(job_id: int) -> tuple[str, dict[str, int]]:
    """供 spawn 子进程调用；子进程自行创建数据库会话。"""
    from src.database import SessionLocal

    db = SessionLocal()
    try:
        row = db.get(MaintenanceJob, job_id)
        if row is None or row.status != ProcessingStatus.PROCESSING.value:
            raise ValueError("维护任务不存在或未处于 processing 状态")
        return build_job_snapshot(db, row)
    finally:
        db.close()


def create_maintenance_job(db, kind: str) -> MaintenanceJob:
    if kind not in _KINDS:
        raise ValueError("未知维护任务类型")
    existing = db.scalar(
        select(MaintenanceJob).where(
            MaintenanceJob.kind == kind,
            MaintenanceJob.status.in_(
                [ProcessingStatus.PENDING.value, ProcessingStatus.PROCESSING.value]
            ),
        )
    )
    if existing is not None:
        raise MaintenanceConflict("同类索引任务已在等待或执行")
    row = MaintenanceJob(
        kind=kind,
        status=ProcessingStatus.PENDING.value,
        attempts=0,
        input_count=0,
        input_chars=0,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def claim_maintenance_job(db, job_id: int, *, max_attempts: int) -> bool:
    result = db.execute(
        update(MaintenanceJob)
        .where(
            MaintenanceJob.id == job_id,
            MaintenanceJob.status.in_(
                [ProcessingStatus.PENDING.value, ProcessingStatus.FAILED.value]
            ),
            MaintenanceJob.attempts < max_attempts,
        )
        .values(
            status=ProcessingStatus.PROCESSING.value,
            attempts=MaintenanceJob.attempts + 1,
            started_at=utcnow_naive(),
            finished_at=None,
            error_code=None,
            error_message=None,
        )
        .execution_options(synchronize_session=False)
    )
    db.commit()
    return bool(result.rowcount)


async def sweep_maintenance_jobs(db, *, stale_minutes: int, max_attempts: int) -> int:
    """Worker 启动时恢复未入队或执行中断的维护任务。"""
    from src.services.queue import push_job

    cutoff = utcnow_naive() - timedelta(minutes=stale_minutes)
    rows = list(
        db.scalars(
            select(MaintenanceJob).where(
                MaintenanceJob.status.in_(
                    [ProcessingStatus.PENDING.value, ProcessingStatus.PROCESSING.value]
                )
            )
        )
    )
    candidates: list[tuple[str, int]] = []
    for row in rows:
        if row.status == ProcessingStatus.PROCESSING.value:
            started_at = row.started_at
            if started_at is not None and started_at.tzinfo is not None:
                started_at = started_at.replace(tzinfo=None)
            if started_at is not None and started_at > cutoff:
                continue
            if row.attempts >= max_attempts:
                row.status = ProcessingStatus.FAILED.value
                row.error_code = "attempts_exhausted"
                row.error_message = "worker sweep: 索引任务超时且达到最大尝试次数"
                row.finished_at = utcnow_naive()
                continue
            row.status = ProcessingStatus.PENDING.value
            row.started_at = None
        elif row.attempts >= max_attempts:
            row.status = ProcessingStatus.FAILED.value
            row.error_code = "attempts_exhausted"
            row.error_message = "worker sweep: 索引任务达到最大尝试次数"
            row.finished_at = utcnow_naive()
            continue
        candidates.append((row.kind, row.id))
    db.commit()

    pushed = 0
    for kind, job_id in candidates:
        if await push_job(kind, job_id):
            pushed += 1
    return pushed


async def process_maintenance_job(job_id: int, db=None) -> str:
    """独立 worker 入口；构建器失败时不改变活动版本。"""
    from src.database import SessionLocal
    owns_session = db is None
    session = db or SessionLocal()
    try:
        if not claim_maintenance_job(
            session, job_id, max_attempts=settings.upload_task_max_attempts
        ):
            return "not_claimed"
        row = session.get(MaintenanceJob, job_id)
        if row is None:
            return "not_found"

        if owns_session:
            from src.workers.isolated_runner import run_isolated

            version, stats = await asyncio.to_thread(
                run_isolated,
                "src.services.maintenance_jobs:build_maintenance_snapshot",
                args=(job_id,),
                timeout_seconds=settings.index_task_timeout_seconds,
            )
        else:
            version, stats = build_job_snapshot(session, row)
        row.output_version = version
        row.input_count = stats["input_count"]
        row.input_chars = stats["input_chars"]
        row.status = ProcessingStatus.READY.value
        row.finished_at = utcnow_naive()
        session.commit()
        return "ready"
    except Exception as exc:
        session.rollback()
        row = session.get(MaintenanceJob, job_id)
        if row is not None:
            row.status = ProcessingStatus.FAILED.value
            row.error_code = "index_build_failed"
            row.error_message = str(exc)[:1000]
            row.finished_at = utcnow_naive()
            session.commit()
        return "failed"
    finally:
        if owns_session:
            session.close()
