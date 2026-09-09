"""faster-whisper 音频转写服务（v1.4）

- 模型懒加载单例（仅 worker 内首次消费时加载，不阻塞服务启动）。
- 本地 CTranslate2 目录加载，无需联网下载；PyAV 内部解码，无需系统 ffmpeg。
- faster_whisper 仅在 get_whisper_model() 内 import —— 测试不装/不 import 也能离线跑。
"""
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Tuple

from config import settings

logger = logging.getLogger(__name__)

_whisper_model = None  # 进程级懒加载单例


@dataclass
class TranscribeResult:
    """转写结果"""
    text: str
    language: Optional[str] = None
    duration_ms: Optional[int] = None
    segments: List[Tuple[float, float, str]] = field(default_factory=list)  # (start,end,text)


def get_whisper_model():
    """懒加载 faster-whisper 模型（函数内 import，测试离线安全）。"""
    global _whisper_model
    if _whisper_model is None:
        from faster_whisper import WhisperModel  # noqa: PLC0415  # lazy import

        logger.info(
            f"加载 Whisper 模型: {settings.whisper_model_dir} "
            f"(device={settings.whisper_device}, compute_type={settings.whisper_compute_type})"
        )
        _whisper_model = WhisperModel(
            settings.whisper_model_dir,
            device=settings.whisper_device,
            compute_type=settings.whisper_compute_type,
            cpu_threads=settings.whisper_cpu_threads,
        )
    return _whisper_model


def reset_whisper_model() -> None:
    """释放模型实例（测试/热更模型用）。"""
    global _whisper_model
    _whisper_model = None


def transcribe_audio_file(path: str, language: Optional[str] = None) -> TranscribeResult:
    """转写单个音频文件。

    Args:
        path: 音频文件绝对路径
        language: 识别语言；None 用 settings.whisper_language

    Returns:
        TranscribeResult

    Raises:
        FileNotFoundError: 文件不存在
        解码/推理异常向上抛（worker 捕获后写 FAILED）
    """
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"音频文件不存在: {path}")

    model = get_whisper_model()
    segments_iter, info = model.transcribe(
        str(p),
        language=language or settings.whisper_language or None,
        beam_size=settings.whisper_beam_size,
        vad_filter=False,
    )

    texts: List[str] = []
    segs: List[Tuple[float, float, str]] = []
    for seg in segments_iter:
        texts.append(seg.text)
        segs.append((seg.start, seg.end, seg.text))

    text = "".join(texts).strip()
    if not text:
        logger.warning(f"转写为空文本: {path}")
    return TranscribeResult(
        text=text,
        language=getattr(info, "language", None),
        duration_ms=int(getattr(info, "duration", 0) * 1000) if getattr(info, "duration", None) else None,
        segments=segs,
    )
