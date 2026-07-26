"""音频转写服务 — Whisper 语音转文字"""
import logging
import io
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


def transcribe_audio(file_bytes: bytes, filename: str) -> Optional[str]:
    """使用 Whisper 转写音频文件"""
    try:
        import whisper
        model = whisper.load_model("base")  # tiny/base/small/medium/large
        # 写入临时文件
        tmp = Path("data/media/audio") / f"_tmp_{filename}"
        tmp.parent.mkdir(parents=True, exist_ok=True)
        tmp.write_bytes(file_bytes)
        result = model.transcribe(str(tmp))
        tmp.unlink()  # 删临时文件
        return result.get("text", "")
    except ImportError:
        logger.warning("whisper 未安装，音频转写不可用。pip install openai-whisper")
        return None
    except Exception as e:
        logger.warning(f"音频转写失败: {e}")
        return None
