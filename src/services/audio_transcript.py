"""音频转写 sidecar 服务（v1.4）：状态机 + Redis 入队 + worker 启动 sweep

状态机：UPLOADED → TRANSCRIBING → INDEXED | FAILED
- `claim_job`：CAS（Compare-And-Swap）抢占——只有 UPLOADED/FAILED 且 attempts<上限 的行可被置为
  TRANSCRIBING 并 attempts+1。并发多 worker（含将来扩容）下至多一个抢到。
- `full_text` 持久化：转写是 CPU 重活，full_text 已存在时失败重试只重切块入索引，不二次转写（幂等省钱）。
- `enqueue_pending_jobs`：worker 启动 sweep——把 Redis 离线期积压的 UPLOADED / 卡死的陈旧 TRANSCRIBING
  （超 `audio_stale_minutes`）复位重入队；达最大尝试的直接置 FAILED 留 error 审计。

时间统一用 naive UTC（`datetime.now(timezone.utc).replace(tzinfo=None)`）：与 SQLite 无 tz 存储天然一致，
MySQL 亦按 UTC 语义存储，陈旧判定在 Python 侧比较不受驱动时区差异影响。
"""
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import select, update

from config import settings
from src.models.audio_transcript import AudioTranscript, AudioTranscriptStatus
from src.services.queue import push_audio_job

logger = logging.getLogger(__name__)

# 状态别名，减少反复写 .value
_UPLOADED = AudioTranscriptStatus.UPLOADED.value
_TRANSCRIBING = AudioTranscriptStatus.TRANSCRIBING.value
_INDEXED = AudioTranscriptStatus.INDEXED.value
_FAILED = AudioTranscriptStatus.FAILED.value


# --------------------------------------------------------------------------- #
# 时间工具
# --------------------------------------------------------------------------- #
def _utcnow_naive() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _as_naive_utc(dt: Optional[datetime]) -> Optional[datetime]:
    """统一为 naive UTC 便于 Python 侧比较（读回 SQLite 的是 naive，MySQL 可能带 tz）。"""
    if dt is None:
        return None
    if dt.tzinfo is not None:
        return dt.astimezone(timezone.utc).replace(tzinfo=None)
    return dt


# --------------------------------------------------------------------------- #
# 基础读写
# --------------------------------------------------------------------------- #
def create_transcript(db, media_id: int, craft_name: str) -> AudioTranscript:
    """幂等建 sidecar 行（UPLOADED, attempts=0）。已存在直接返回现有行。"""
    existing = get_transcript(db, media_id)
    if existing is not None:
        return existing
    row = AudioTranscript(
        media_id=media_id,
        craft_name=craft_name,
        status=_UPLOADED,
        attempts=0,
    )
    db.add(row)
    try:
        db.commit()
    except Exception:  # 并发同 media_id 竞态 → 回滚后取已存在行
        db.rollback()
        return get_transcript(db, media_id)
    db.refresh(row)
    return row


def get_transcript(db, media_id: int) -> Optional[AudioTranscript]:
    return db.execute(
        select(AudioTranscript).where(AudioTranscript.media_id == media_id)
    ).scalar_one_or_none()


# --------------------------------------------------------------------------- #
# CAS 抢占 / 标记
# --------------------------------------------------------------------------- #
def claim_job(db, media_id: int) -> bool:
    """CAS 抢占：UPLOADED/FAILED 且 attempts<上限 → TRANSCRIBING + attempts+1 + started_at。

    返回是否抢到。rowcount 才是判据（高并发下 UPDATE 天然串行化）。"
    """
    now = _utcnow_naive()
    result = db.execute(
        update(AudioTranscript)
        .where(
            AudioTranscript.media_id == media_id,
            AudioTranscript.status.in_([_UPLOADED, _FAILED]),
            AudioTranscript.attempts < settings.audio_max_attempts,
        )
        .values(
            status=_TRANSCRIBING,
            attempts=AudioTranscript.attempts + 1,
            started_at=now,
            error=None,  # 重试时清旧错误
        )
        .execution_options(synchronize_session=False)
    )
    db.commit()
    return bool(result.rowcount)


def mark_success(
    db,
    media_id: int,
    *,
    language: Optional[str],
    duration_ms: Optional[int],
    full_text: str,
    chunk_count: int,
) -> None:
    db.execute(
        update(AudioTranscript)
        .where(AudioTranscript.media_id == media_id)
        .values(
            status=_INDEXED,
            language=language,
            duration_ms=duration_ms,
            full_text=full_text,
            chunk_count=chunk_count,
            error=None,
            finished_at=_utcnow_naive(),
        )
        .execution_options(synchronize_session=False)
    )
    db.commit()


def mark_failed(db, media_id: int, error: str) -> None:
    db.execute(
        update(AudioTranscript)
        .where(AudioTranscript.media_id == media_id)
        .values(
            status=_FAILED,
            error=(error or "")[:500],
            finished_at=_utcnow_naive(),
        )
        .execution_options(synchronize_session=False)
    )
    db.commit()


# --------------------------------------------------------------------------- #
# 入队 / sweep
# --------------------------------------------------------------------------- #
async def ensure_audio_job(db, media_id: int, craft_name: str) -> AudioTranscript:
    """上传后接线：幂等建 sidecar + 入队转写。

    仅当行处于可重入状态（UPLOADED/FAILED 且未达最大尝试）才入队；INDEXED/TRANSCRIBING 不动。
    入队失败仅 warning，不阻断上传（worker 启动 sweep 会兜底重入队）。
    """
    row = create_transcript(db, media_id, craft_name)
    if row.attempts < settings.audio_max_attempts and row.status in (_UPLOADED, _FAILED):
        ok = await push_audio_job(media_id)
        if not ok:
            logger.warning(f"media_id={media_id} 转写任务入队失败（保持 {row.status}，worker sweep 兜底）")
    return row


async def enqueue_pending_jobs(db) -> int:
    """worker 启动 sweep：复位陈旧 TRANSCRIBING + 重入队积压 UPLOADED。返回成功入队条数。

    - 陈旧 TRANSCRIBING（started_at 超 audio_stale_minutes 未完成，说明 worker 转写中崩了）：
      attempts 未达上限 → 复位 UPLOADED 重入队（full_text 已存在则只重索引）；达上限 → FAILED + error。
    - UPLOADED 达上限同理直接 FAILED（避免无限重试）。
    """
    now = _utcnow_naive()
    stale_cutoff = now - timedelta(minutes=settings.audio_stale_minutes)
    rows = db.execute(
        select(AudioTranscript).where(
            AudioTranscript.status.in_([_UPLOADED, _TRANSCRIBING])
        )
    ).scalars().all()

    pushed = 0
    for row in rows:
        if row.status == _TRANSCRIBING:
            started = _as_naive_utc(row.started_at)
            if started is not None and started > stale_cutoff:
                continue  # 仍在转写窗口内，不动
            if row.attempts >= settings.audio_max_attempts:
                _terminalize(row, "worker sweep: 转写卡死且达最大尝试次数")
                continue
            row.status = _UPLOADED  # 复位，让 claim 可重取
            logger.info(f"media_id={row.media_id} 陈旧 TRANSCRIBING 复位重入队 (attempts={row.attempts})")
        # status == UPLOADED
        if row.attempts >= settings.audio_max_attempts:
            _terminalize(row, "worker sweep: 达最大尝试次数，转 FAILED")
            continue
        if await push_audio_job(row.media_id):
            pushed += 1
    db.commit()
    return pushed


def _terminalize(row: AudioTranscript, error: str) -> None:
    """就地置 FAILED（由 enqueue_pending_jobs 统一 commit）。"""
    row.status = _FAILED
    row.error = error[:500]
    row.finished_at = _utcnow_naive()
