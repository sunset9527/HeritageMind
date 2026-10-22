"""音频解码、时长和转写文本边界必须在模型加载前生效。"""

import pytest

from src.services import transcription


def test_undecodable_audio_fails_before_whisper_load(tmp_path, monkeypatch):
    path = tmp_path / "broken.mp3"
    path.write_bytes(b"ID3not-audio")
    loaded = {"called": False}
    monkeypatch.setattr(
        transcription,
        "get_whisper_model",
        lambda: loaded.update(called=True),
    )

    with pytest.raises(transcription.AudioValidationError):
        transcription.transcribe_audio_file(str(path))
    assert loaded["called"] is False


def test_audio_over_thirty_minutes_fails_before_whisper_load(tmp_path, monkeypatch):
    path = tmp_path / "long.wav"
    path.write_bytes(b"RIFFxxxxWAVE")
    loaded = {"called": False}
    monkeypatch.setattr(transcription, "probe_audio_duration_seconds", lambda _: 1800.1)
    monkeypatch.setattr(
        transcription,
        "get_whisper_model",
        lambda: loaded.update(called=True),
    )

    with pytest.raises(transcription.AudioValidationError) as error:
        transcription.transcribe_audio_file(str(path))
    assert error.value.code == "audio_duration_exceeded"
    assert loaded["called"] is False


def test_unknown_audio_duration_fails_closed(tmp_path, monkeypatch):
    path = tmp_path / "unknown.ogg"
    path.write_bytes(b"OggSxxxx")
    monkeypatch.setattr(transcription, "probe_audio_duration_seconds", lambda _: None)
    with pytest.raises(transcription.AudioValidationError) as error:
        transcription.validate_audio_duration(path, max_seconds=1800)
    assert error.value.code == "audio_duration_unknown"
