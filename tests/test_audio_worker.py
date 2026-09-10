"""v1.4 音频转写 worker 测试（离线：sqlite in-memory + 注入转写/向量桩 + Redis 队列桩）。

覆盖：单任务全链路 UPLOADED→INDEXED（full_text 落库）、异常→FAILED+attempts、
重复 claim 拒绝、full_text 已存在跳过二次转写只重索引、文件缺失→FAILED、
启动 sweep（陈旧 TRANSCRIBING 复位重入队 / 达上限转 FAILED）。
"""
import asyncio
from datetime import timedelta
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import src.models  # noqa: F401  # 注册全部模型到 Base.metadata
from config import settings
from src.database import Base
from src.models.audio_transcript import AudioTranscript, AudioTranscriptStatus
from src.models.media import MediaDocument, MediaType
from src.services import audio_transcript as at_svc
from src.services import audio_worker as worker
from src.services import queue
from src.services.transcription import TranscribeResult
from tests.redis_stub import StubRedis


# --------------------------------------------------------------------------- #
# 桩
# --------------------------------------------------------------------------- #
class _StoreStub:
    """替身 get_audio_store()：记录调用并假装入库 N 块。"""

    def __init__(self, chunk_count=3):
        self.chunk_count = chunk_count
        self.calls = []

    def index_transcript(self, media_id, craft_name, title, full_text):
        self.calls.append((media_id, craft_name, title, full_text))
        return self.chunk_count


def _stub_transcribe(path):
    """同步桩转写：返回固定中文文本（worker 经 asyncio.to_thread 调用）。"""
    return TranscribeResult(
        text="景泰蓝的掐丝工艺历史悠久，历经百年传承。",
        language="zh",
        duration_ms=1500,
        segments=[(0.0, 1.5, "景泰蓝的掐丝工艺历史悠久，历经百年传承。")],
    )


# --------------------------------------------------------------------------- #
# fixtures
# --------------------------------------------------------------------------- #
@pytest.fixture()
def db():
    """独立 sqlite in-memory 会话（StaticPool 单连接，跨 to_thread 无碍）。"""
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    # 默认 expire_on_commit=True：claim/mark 用 update()+synchronize_session=False 改库后，
    # 旧对象属性访问会自动重查，避免读到陈旧 status
    sess = sessionmaker(bind=engine)()
    yield sess
    sess.close()


@pytest.fixture()
def storage(monkeypatch, tmp_path):
    """把 worker 的 STORAGE_ROOT 指到临时目录（media 全局 STORAGE_ROOT 在 import 时已定）。"""
    monkeypatch.setattr(worker, "STORAGE_ROOT", Path(tmp_path))
    return Path(tmp_path)


def _mk_media(db, *, craft_name="景泰蓝", filename="clip.wav", title="大师访谈"):
    """插入一条 audio 型 media_documents，返回 (media_id, 文件绝对路径占位)。"""
    doc = MediaDocument(
        craft_name=craft_name,
        media_type=MediaType.AUDIO,
        filename=filename,
        original_name=filename,
        mime_type="audio/wav",
        size=1024,
        title=title,
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)
    return doc.id


def _mk_sidecar(db, media_id, *, craft_name="景泰蓝", status=AudioTranscriptStatus.UPLOADED, attempts=0, full_text=None):
    row = AudioTranscript(
        media_id=media_id,
        craft_name=craft_name,
        status=status.value,
        attempts=attempts,
        full_text=full_text,
    )
    db.add(row)
    db.commit()
    return row


def _write_audio(storage, filename="clip.wav"):
    f = storage / "audio" / filename
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_bytes(b"RIFF....WAVE fake audio")
    return f


@pytest.fixture()
def store_stub(monkeypatch):
    s = _StoreStub()
    monkeypatch.setattr(worker, "get_audio_store", lambda: s)
    return s


@pytest.fixture()
def transcribe_stub(monkeypatch):
    monkeypatch.setattr(worker, "transcribe_audio_file", _stub_transcribe)


# --------------------------------------------------------------------------- #
# 全链路
# --------------------------------------------------------------------------- #
def test_full_job_uploaded_to_indexed(db, storage, store_stub, transcribe_stub):
    mid = _mk_media(db)
    _mk_sidecar(db, mid)
    _write_audio(storage)
    result = asyncio.run(worker.process_one_job(mid, db=db))
    assert result == "indexed"
    row = at_svc.get_transcript(db, mid)
    assert row.status == AudioTranscriptStatus.INDEXED.value
    assert row.attempts == 1  # claim +1
    assert row.full_text and "掐丝" in row.full_text
    assert row.chunk_count == 3
    assert row.language == "zh"
    assert row.duration_ms == 1500
    assert store_stub.calls == [(mid, "景泰蓝", "大师访谈", row.full_text)]


def test_transcribe_exception_marks_failed_and_increments_attempts(db, storage, store_stub, monkeypatch):
    def _boom(path):
        raise RuntimeError("whisper boom")

    monkeypatch.setattr(worker, "transcribe_audio_file", _boom)
    mid = _mk_media(db)
    _mk_sidecar(db, mid)
    _write_audio(storage)
    result = asyncio.run(worker.process_one_job(mid, db=db))
    assert result == "error"
    row = at_svc.get_transcript(db, mid)
    assert row.status == AudioTranscriptStatus.FAILED.value
    assert row.attempts == 1
    assert "boom" in (row.error or "")


def test_file_missing_marks_failed(db, storage, store_stub, transcribe_stub):
    mid = _mk_media(db)  # 不写文件
    _mk_sidecar(db, mid)
    result = asyncio.run(worker.process_one_job(mid, db=db))
    assert result == "file_missing"
    row = at_svc.get_transcript(db, mid)
    assert row.status == AudioTranscriptStatus.FAILED.value
    assert "缺失" in (row.error or "")
    assert store_stub.calls == []  # 未入库


def test_no_sidecar_skips(db, storage, store_stub, transcribe_stub):
    result = asyncio.run(worker.process_one_job(9999, db=db))
    assert result == "not_claimed"  # claim 前无行 → UPDATE rowcount=0


def test_full_text_present_skips_retranscribe(db, storage, store_stub, monkeypatch):
    """full_text 已存在：绝不二次转写，只重建向量索引。"""
    called = {"n": 0}

    def _should_not_call(path):
        called["n"] += 1
        raise AssertionError("full_text 已存在，不应再次转写")

    monkeypatch.setattr(worker, "transcribe_audio_file", _should_not_call)
    mid = _mk_media(db)
    existing = "首次转写已完成但入库前中断的文本。"
    _mk_sidecar(db, mid, status=AudioTranscriptStatus.FAILED, attempts=1, full_text=existing)
    _write_audio(storage)
    result = asyncio.run(worker.process_one_job(mid, db=db))
    assert result == "indexed"
    assert called["n"] == 0  # 未触发二次转写
    row = at_svc.get_transcript(db, mid)
    assert row.full_text == existing
    assert row.status == AudioTranscriptStatus.INDEXED.value
    assert store_stub.calls == [(mid, "景泰蓝", "大师访谈", existing)]


# --------------------------------------------------------------------------- #
# claim CAS
# --------------------------------------------------------------------------- #
def test_claim_once_only(db):
    mid = _mk_media(db)
    _mk_sidecar(db, mid)
    assert at_svc.claim_job(db, mid) is True
    row = at_svc.get_transcript(db, mid)
    assert row.status == AudioTranscriptStatus.TRANSCRIBING.value
    assert row.attempts == 1
    assert at_svc.claim_job(db, mid) is False  # 已是 TRANSCRIBING，不能二次抢
    assert at_svc.get_transcript(db, mid).attempts == 1


def test_claim_failed_retry_until_max(db, monkeypatch):
    monkeypatch.setattr(settings, "audio_max_attempts", 3)
    mid = _mk_media(db)
    row = _mk_sidecar(db, mid)
    for i in range(1, 4):
        assert at_svc.claim_job(db, mid) is True, f"第 {i} 次应可抢"
        # 模拟失败后回到 FAILED
        at_svc.mark_failed(db, mid, f"err{i}")
    # 已达上限：FAILED 不再可抢
    assert at_svc.claim_job(db, mid) is False
    assert at_svc.get_transcript(db, mid).attempts == 3


# --------------------------------------------------------------------------- #
# 启动 sweep（enqueue_pending_jobs）
# --------------------------------------------------------------------------- #
@pytest.fixture()
def redis_stub(monkeypatch):
    s = StubRedis()
    monkeypatch.setattr(queue, "_redis", s)
    return s


def _sweep(db):
    return asyncio.run(at_svc.enqueue_pending_jobs(db))


def test_sweep_enqueues_uploaded(db, redis_stub):
    mid = _mk_media(db)
    _mk_sidecar(db, mid)  # UPLOADED attempts=0
    assert _sweep(db) == 1
    assert len(redis_stub.lists[settings.audio_queue_key]) == 1


def test_sweep_resets_stale_transcribing(db, redis_stub, monkeypatch):
    monkeypatch.setattr(settings, "audio_stale_minutes", 15)
    mid = _mk_media(db)
    row = _mk_sidecar(db, mid, status=AudioTranscriptStatus.TRANSCRIBING, attempts=1)
    row.started_at = at_svc._utcnow_naive() - timedelta(minutes=30)
    db.commit()
    assert _sweep(db) == 1  # 复位 UPLOADED 并重入队
    row = at_svc.get_transcript(db, mid)
    assert row.status == AudioTranscriptStatus.UPLOADED.value
    assert len(redis_stub.lists[settings.audio_queue_key]) == 1


def test_sweep_leaves_recent_transcribing(db, redis_stub):
    mid = _mk_media(db)
    row = _mk_sidecar(db, mid, status=AudioTranscriptStatus.TRANSCRIBING, attempts=1)
    row.started_at = at_svc._utcnow_naive()  # 刚刚开始，未陈旧
    db.commit()
    assert _sweep(db) == 0  # 不动，不入队
    assert at_svc.get_transcript(db, mid).status == AudioTranscriptStatus.TRANSCRIBING.value


def test_sweep_terminalizes_exhausted_uploaded(db, redis_stub, monkeypatch):
    monkeypatch.setattr(settings, "audio_max_attempts", 3)
    mid = _mk_media(db)
    _mk_sidecar(db, mid, status=AudioTranscriptStatus.UPLOADED, attempts=3)
    assert _sweep(db) == 0
    row = at_svc.get_transcript(db, mid)
    assert row.status == AudioTranscriptStatus.FAILED.value
    assert "最大尝试" in (row.error or "")
    assert settings.audio_queue_key not in redis_stub.lists  # 未入队
