"""
v1.4 音频 sidecar 表模型测试（纯 SQLAlchemy，零网络/零第三方服务）。

覆盖：
① create_all 能新建 audio_transcripts（含 media_documents，验证 FK 目标存在）
② 字段/枚举/默认值/唯一约束
③ media_id 唯一：同 media_id 二次插入抛 IntegrityError
"""
import pytest
from sqlalchemy import create_engine, inspect
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from src.database import Base
from src.models.audio_transcript import AudioTranscript, AudioTranscriptStatus
from src.models.media import MediaDocument


@pytest.fixture()
def engine():
    eng = create_engine("sqlite://")
    Base.metadata.create_all(eng)
    return eng


def test_table_created(engine):
    insp = inspect(engine)
    assert "audio_transcripts" in insp.get_table_names()


def test_columns_and_defaults(engine):
    insp = inspect(engine)
    cols = {c["name"]: c for c in insp.get_columns("audio_transcripts")}
    assert "media_id" in cols and "full_text" in cols and "chunk_count" in cols
    assert "craft_name" in cols and "status" in cols and "attempts" in cols


def test_status_enum_values():
    assert AudioTranscriptStatus.UPLOADED.value == "UPLOADED"
    assert [s.value for s in AudioTranscriptStatus] == [
        "UPLOADED", "TRANSCRIBING", "INDEXED", "FAILED",
    ]


def test_row_defaults(engine):
    with Session(engine) as s:
        m = MediaDocument(
            craft_name="景泰蓝", media_type="audio",
            filename="a.wav", original_name="a.wav",
            mime_type="audio/wav", size=10,
        )
        s.add(m)
        s.commit()
        t = AudioTranscript(media_id=m.id, craft_name="景泰蓝")
        s.add(t)
        s.commit()
        s.refresh(t)
        assert t.status == AudioTranscriptStatus.UPLOADED.value
        assert t.attempts == 0
        assert t.chunk_count == 0
        assert t.full_text is None


def test_media_id_unique(engine):
    with Session(engine) as s:
        m = MediaDocument(
            craft_name="苏绣", media_type="audio",
            filename="b.wav", original_name="b.wav",
            mime_type="audio/wav", size=10,
        )
        s.add(m)
        s.commit()
        s.add(AudioTranscript(media_id=m.id, craft_name="苏绣"))
        s.commit()
        s.add(AudioTranscript(media_id=m.id, craft_name="苏绣"))
        with pytest.raises(IntegrityError):
            s.commit()
