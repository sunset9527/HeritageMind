"""音频转写 worker（v1.4）：单 asyncio 任务消费 Redis 队列，逐条转写 → 向量入库 → 标记。

- `process_one_job(media_id[, db])`：单任务全链路。先 `claim_job`（CAS）——抢不到（并发/达上限）即返回；
  抢到后文件缺失/转写失败 → `mark_failed`（attempts 由 claim 累加）；成功 → `index_transcript` + `mark_success`。
  CPU 重活（faster-whisper 推理、BGE 向量化）一律 `asyncio.to_thread`，不阻塞事件循环。
  full_text 已存在（上次中断于"转写完成、入库前"）→ 跳过二次转写，只重切块入索引（幂等省钱）。
- `run_worker(stop_event)`：Redis 不可达直接不启动（不空转）；启动先 `enqueue_pending_jobs` sweep
  （兜底 Redis 离线期积压），再 BLPOP 轮询。单条异常不杀 worker。
- 独立 SessionLocal 会话：与 API 请求会话隔离，长任务不占连接。

多进程/热重载重复启动假设：单 worker（README 注明）。claim CAS + chroma delete-add 保证 at-least-once 幂等。
"""
import asyncio
import logging

from config import settings
from src.database import SessionLocal
from src.retrieval.audio_store import get_audio_store
from src.services.audio_transcript import (
    claim_job,
    enqueue_pending_jobs,
    get_transcript,
    mark_failed,
    mark_success,
)
from src.services.media import STORAGE_ROOT, get_media
from src.services.queue import get_redis, pop_audio_job
from src.services.transcription import transcribe_audio_file

logger = logging.getLogger(__name__)


def _index_transcript(media_id: int, craft_name: str, title: str, full_text: str) -> int:
    """在 to_thread 中执行：faster-whisper/BGE 都是 CPU 重活，不能阻塞事件循环。"""
    return get_audio_store().index_transcript(media_id, craft_name, title, full_text)


async def process_one_job(media_id: int, db=None) -> str:
    """处理单条转写任务。返回结果标签（not_claimed/bad_media/file_missing/empty_transcript/indexed/error）。

    db 可注入（测试用 sqlite 会话）；默认独立开 SessionLocal。谁开谁关。
    """
    owns_session = db is None
    session = db or SessionLocal()
    try:
        if not claim_job(session, media_id):
            logger.info(f"media_id={media_id} 抢占失败（并发处理中或已达最大尝试），跳过")
            return "not_claimed"

        row = get_transcript(session, media_id)
        media = get_media(session, media_id)
        if media is None or getattr(media, "media_type", None) is None or media.media_type.value != "audio":
            mark_failed(session, media_id, "media_documents 不存在或非 audio 类型")
            return "bad_media"
        file_path = STORAGE_ROOT / media.media_type.value / media.filename
        if not file_path.exists():
            mark_failed(session, media_id, f"音频文件缺失: {file_path}")
            return "file_missing"

        full_text = (row.full_text or "").strip() if row else ""
        if full_text:
            # 上次中断于"转写完成、入库前"——只重索引，不再花 CPU 二次转写
            language, duration_ms = row.language, row.duration_ms
            logger.info(f"media_id={media_id} full_text 已存在，跳过二次转写，仅重建向量索引")
        else:
            result = await asyncio.to_thread(transcribe_audio_file, str(file_path))
            full_text = (result.text or "").strip()
            language, duration_ms = result.language, result.duration_ms
            if not full_text:
                mark_failed(session, media_id, "转写结果为空文本（可能为静音/纯音乐）")
                return "empty_transcript"

        chunk_count = await asyncio.to_thread(
            _index_transcript, media_id, row.craft_name, media.title, full_text
        )
        mark_success(
            session,
            media_id,
            language=language,
            duration_ms=duration_ms,
            full_text=full_text,
            chunk_count=chunk_count,
        )
        logger.info(f"media_id={media_id} 转写入库完成: {chunk_count} chunks ({len(full_text)} chars)")
        return "indexed"
    except Exception as e:
        session.rollback()
        try:
            mark_failed(session, media_id, str(e))
        except Exception:
            session.rollback()
        logger.error(f"media_id={media_id} 转写任务失败: {e}")
        return "error"
    finally:
        if owns_session:
            session.close()


async def run_worker(stop_event: asyncio.Event) -> None:
    """worker 主循环：启动 sweep + BLPOP 轮询，直到 stop_event 置位。"""
    if not settings.audio_worker_enabled:
        logger.info("audio_worker_enabled=False，跳过转写 worker")
        return

    # 先探测 Redis：不可达就不空转（积压留在 DB，下次启动 sweep 兜底）
    try:
        await get_redis().ping()
    except Exception as e:
        logger.warning(f"Redis 不可达，转写 worker 不启动: {e}")
        return

    db = SessionLocal()
    try:
        swept = await enqueue_pending_jobs(db)
        logger.info(f"转写 worker 启动 sweep: 复位/重入队 {swept} 条积压任务")
    finally:
        db.close()

    logger.info("音频转写 worker 启动（BLPOP 轮询队列）")
    while not stop_event.is_set():
        media_id = await pop_audio_job(timeout=1)
        if media_id is None:  # 空队列超时
            continue
        try:
            await process_one_job(media_id)
        except Exception as e:
            logger.error(f"process_one_job 未捕获异常 media_id={media_id}: {e}")
    logger.info("音频转写 worker 退出")
