"""
v1.4 转写服务测试（零网络；monkeypatch get_whisper_model 返回桩，不 import faster_whisper）。
"""
import pytest

from src.services import transcription
from src.services.transcription import (
    TranscribeResult,
    get_whisper_model,
    reset_whisper_model,
    transcribe_audio_file,
)


class _Seg:
    def __init__(self, start, end, text):
        self.start, self.end, self.text = start, end, text


class _Info:
    language = "zh"
    duration = 3.5


class _StubModel:
    """模拟 faster_whisper.WhisperModel：transcribe 返回 (segment 生成器, info)。"""

    def __init__(self, text_parts):
        self._parts = text_parts

    def transcribe(self, path, **kwargs):
        segs = (_Seg(0.0, 1.0, t) for t in self._parts)
        return segs, _Info()


def _patch_model(monkeypatch, parts, tmp_path):
    audio = tmp_path / "a.wav"
    audio.write_bytes(b"RIFF....")
    monkeypatch.setattr(transcription, "get_whisper_model", lambda: _StubModel(parts))
    return audio


def test_result_text_and_meta(monkeypatch, tmp_path):
    audio = _patch_model(monkeypatch, ["你好", " 景泰蓝"], tmp_path)
    r = transcribe_audio_file(str(audio))
    assert isinstance(r, TranscribeResult)
    assert r.language == "zh"
    assert r.duration_ms == 3500
    assert r.segments and r.segments[0][2] == "你好"


def test_empty_text(monkeypatch, tmp_path):
    audio = _patch_model(monkeypatch, ["   "], tmp_path)
    r = transcribe_audio_file(str(audio))
    assert r.text == ""


def test_file_missing_raises(monkeypatch, tmp_path):
    monkeypatch.setattr(transcription, "get_whisper_model", lambda: _StubModel(["x"]))
    with pytest.raises(FileNotFoundError):
        transcribe_audio_file(str(tmp_path / "nope.wav"))


def test_get_whisper_model_returns_stub(monkeypatch):
    """worker 依赖的 get_whisper_model 可被整体替换（注入点成立）。"""
    marker = object()
    monkeypatch.setattr(transcription, "get_whisper_model", lambda: marker)
    assert transcription.get_whisper_model() is marker


def test_cached_singleton_and_reset(monkeypatch):
    """懒加载缓存：_whisper_model 已置 → get_whisper_model 直接返回不触发 import；reset 清空。"""
    sentinel = object()
    transcription._whisper_model = sentinel
    try:
        assert get_whisper_model() is sentinel
    finally:
        reset_whisper_model()
    assert transcription._whisper_model is None
