"""图片向量化 — 使用 CLIP 模型生成图片嵌入，支持文搜图/以图搜图"""
import io
import logging
import numpy as np
from typing import List, Optional
from pathlib import Path

logger = logging.getLogger(__name__)

# 全局模型缓存
_clip_model = None
_clip_processor = None


def _load_clip():
    """延迟加载 CLIP 模型（首次调用时）"""
    global _clip_model, _clip_processor
    if _clip_model is not None:
        return True
    try:
        from transformers import CLIPModel, CLIPProcessor
        model_name = "openai/clip-vit-base-patch32"
        _clip_model = CLIPModel.from_pretrained(model_name)
        _clip_processor = CLIPProcessor.from_pretrained(model_name)
        logger.info(f"CLIP 模型加载完成: {model_name}")
        return True
    except ImportError:
        logger.warning("transformers 未安装，图片向量化不可用")
        return False
    except Exception as e:
        logger.warning(f"CLIP 模型加载失败: {e}")
        return False


def image_to_embedding(image_bytes: bytes) -> Optional[List[float]]:
    """图片 → 向量"""
    if not _load_clip():
        return None
    try:
        from PIL import Image
        img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        inputs = _clip_processor(images=img, return_tensors="pt")
        outputs = _clip_model.get_image_features(**inputs)
        emb = outputs.detach().numpy().flatten()
        return emb.tolist()
    except Exception as e:
        logger.warning(f"图片向量化失败: {e}")
        return None


def text_to_embedding(text: str) -> Optional[List[float]]:
    """文本 → CLIP 向量（中文用 Chinese-CLIP，此处用英文 CLIP 兜底）"""
    if not _load_clip():
        return None
    try:
        inputs = _clip_processor(text=[text], return_tensors="pt", padding=True, truncation=True)
        outputs = _clip_model.get_text_features(**inputs)
        emb = outputs.detach().numpy().flatten()
        return emb.tolist()
    except Exception as e:
        logger.warning(f"文本向量化失败: {e}")
        return None


def image_file_to_embedding(file_path: Path) -> Optional[List[float]]:
    """从文件路径读取图片并向量化"""
    try:
        return image_to_embedding(file_path.read_bytes())
    except Exception as e:
        logger.warning(f"读取图片失败 {file_path}: {e}")
        return None


def cosine_similarity(a: List[float], b: List[float]) -> float:
    """余弦相似度"""
    a_arr, b_arr = np.array(a), np.array(b)
    return float(np.dot(a_arr, b_arr) / (np.linalg.norm(a_arr) * np.linalg.norm(b_arr) + 1e-8))
