"""HeritageMind 独立上传与维护 worker 入口。"""

from __future__ import annotations

import asyncio
import logging
import os
import socket
import time

from config import settings
from src.app_metadata import APP_VERSION
from src.database import SessionLocal
from src.services.audio_transcript import enqueue_pending_jobs
from src.services.audio_worker import process_one_job as process_audio_job
from src.services.queue import get_redis, pop_audio_job, pop_job
from src.services.task_state import sweep_document_jobs, update_worker_heartbeat
from src.services.startup_validation import validate_startup_settings
from src.services.concurrency import ConcurrencyBusyError, HighCostCapability, get_concurrency_limiter


logger = logging.getLogger(__name__)


def _worker_id() -> str:
    return os.environ.get("WORKER_ID") or f"{socket.gethostname()}-{os.getpid()}"


async def _dispatch(kind: str, entity_id: int) -> str:
    capability = (
        HighCostCapability.AUDIO_TRANSCRIPTION
        if kind == "audio"
        else HighCostCapability.DOCUMENT_PROCESSING
        if kind == "document"
        else HighCostCapability.INDEX_REBUILD
    )
    try:
        async with get_concurrency_limiter().permit(capability):
            if kind == "audio":
                return await process_audio_job(entity_id)
            if kind == "document":
                from src.workers.processors import process_document_job

                return await process_document_job(entity_id)
            from src.services.maintenance_jobs import process_maintenance_job

            return await process_maintenance_job(entity_id)
    except ConcurrencyBusyError:
        logger.warning("后台任务等待并发许可超时 kind=%s entity_id=%s", kind, entity_id)
        return "busy"


async def run_worker(stop_event: asyncio.Event) -> None:
    await get_redis().ping()
    worker_id = _worker_id()
    db = SessionLocal()
    try:
        await enqueue_pending_jobs(db)
        await sweep_document_jobs(
            db,
            stale_minutes=max(1, settings.document_task_timeout_seconds // 60),
            max_attempts=settings.upload_task_max_attempts,
        )
        from src.services.maintenance_jobs import sweep_maintenance_jobs

        await sweep_maintenance_jobs(
            db,
            stale_minutes=max(1, settings.index_task_timeout_seconds // 60),
            max_attempts=settings.upload_task_max_attempts,
        )
        update_worker_heartbeat(db, worker_id, APP_VERSION)
    finally:
        db.close()

    last_heartbeat = time.monotonic()
    while not stop_event.is_set():
        task = await pop_job(timeout=1)
        if task is None:
            audio_id = await pop_audio_job(timeout=0)
            if audio_id is not None:
                await _dispatch("audio", audio_id)
        else:
            try:
                await _dispatch(task.kind, task.entity_id)
            except Exception:
                logger.exception(
                    "后台任务未捕获异常 kind=%s entity_id=%s",
                    task.kind,
                    task.entity_id,
                )
        if time.monotonic() - last_heartbeat >= 15:
            db = SessionLocal()
            try:
                update_worker_heartbeat(db, worker_id, APP_VERSION)
            finally:
                db.close()
            last_heartbeat = time.monotonic()


def main() -> None:
    logging.basicConfig(level=getattr(logging, settings.log_level))
    validate_startup_settings(settings)

    async def start() -> None:
        await run_worker(asyncio.Event())

    try:
        asyncio.run(start())
    except KeyboardInterrupt:
        logger.info("worker 收到退出信号")


if __name__ == "__main__":
    main()
