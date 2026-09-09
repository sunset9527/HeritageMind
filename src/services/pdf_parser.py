# -*- coding: utf-8 -*-
"""
PDF/扫描件解析器 —— 非结构化文档 → 纯文本

处理策略（三级）：
1. 用 fitz(pymupdf) 提取 PDF 文本层：数字原生 PDF 直接拿到文字
2. 页文本层字符数 < 阈值（默认 20 字）判定为「扫描页/图片页」：
   渲染成位图（page.get_pixmap）→ RapidOCR 中文 OCR 兜底
3. OCR 后仍无内容 → 标注 source="empty"（封面页、纯装饰图页），由调用方决定跳过

与 LexRAG 项目 src/ingestion/pdf_parser.py 同一套逻辑的独立副本，
本版本额外支持直接传入文件字节（bytes），便于对接文档上传接口。
"""
import logging
from pathlib import Path
from typing import List, Dict, Optional, Union

logger = logging.getLogger(__name__)

# OCR 引擎单例（模型加载一次，避免每页重复加载）
_ocr_engine = None


def _get_ocr_engine():
    """懒加载 RapidOCR 引擎（首次调用会加载 onnx 模型，耗时几秒）"""
    global _ocr_engine
    if _ocr_engine is None:
        from rapidocr_onnxruntime import RapidOCR
        _ocr_engine = RapidOCR()
        logger.info("RapidOCR 引擎已加载")
    return _ocr_engine


def _open_doc(path_or_bytes: Union[str, Path, bytes]):
    """打开 PDF：支持文件路径或文件字节（bytes）"""
    import fitz
    if isinstance(path_or_bytes, (bytes, bytearray)):
        return fitz.open(stream=bytes(path_or_bytes), filetype="pdf")
    return fitz.open(str(path_or_bytes))


def _ocr_page(page, dpi: int = 200) -> str:
    """
    将 PDF 页渲染为位图并做 OCR

    Args:
        page: fitz.Page 对象
        dpi: 渲染分辨率，扫描件建议 200~300

    Returns:
        OCR 识别出的文本（可能为空字符串）
    """
    import numpy as np

    # 渲染为 RGB 位图（colorspace="rgb" 保证 3 通道，RapidOCR 需要 HWC 数组）
    pix = page.get_pixmap(dpi=dpi, colorspace="rgb")
    img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, 3)

    result, _ = _get_ocr_engine()(img)
    if not result:
        return ""
    # result: [[box, text, score], ...]，按行拼接
    return "\n".join(str(line[1]) for line in result)


def parse_pdf(
    path_or_bytes: Union[str, Path, bytes],
    ocr_fallback: bool = True,
    ocr_char_threshold: int = 20,
) -> List[Dict]:
    """
    解析 PDF，逐页返回提取结果

    Args:
        path_or_bytes: PDF 文件路径 或 文件字节（bytes）
        ocr_fallback: 文本层过少时是否启用 RapidOCR 兜底（默认 True）
        ocr_char_threshold: 页文本层字符数低于该值判定为扫描页（默认 20）

    Returns:
        [{"page": 页码(从1开始), "text": 文本, "source": "text"|"ocr"|"empty", "char_count": 字符数}, ...]

    说明：
    - source="text"  数字原生 PDF，来自文本层
    - source="ocr"   扫描页，来自 RapidOCR
    - source="empty" 封面页/纯图页，无任何文字（OCR 也未识别出内容）
    """
    import fitz

    doc = _open_doc(path_or_bytes)
    pages: List[Dict] = []
    try:
        for idx, page in enumerate(doc, start=1):
            text = page.get_text("text") or ""
            char_count = len(text.strip())
            source = "text"

            # 文本层过少 → 判定为扫描页，走 OCR 兜底
            if char_count < ocr_char_threshold and ocr_fallback:
                try:
                    ocr_text = _ocr_page(page)
                except Exception as e:  # OCR 失败不致命，标注 empty
                    logger.warning(f"第{idx}页 OCR 失败: {e}")
                    ocr_text = ""
                if ocr_text.strip():
                    text = ocr_text
                    char_count = len(ocr_text.strip())
                    source = "ocr"
                else:
                    source = "empty"

            pages.append({
                "page": idx,
                "text": text,
                "source": source,
                "char_count": char_count,
            })
    finally:
        doc.close()
    return pages


def parse_pdf_to_text(
    path_or_bytes: Union[str, Path, bytes],
    ocr_fallback: bool = True,
    pages: Optional[List[Dict]] = None,
) -> str:
    """
    解析 PDF 并返回合并纯文本（跳过封面/空页，页间空行分隔）

    Args:
        path_or_bytes: PDF 文件路径 或 文件字节（bytes）
        ocr_fallback: 是否启用 OCR 兜底
        pages: 可选，传入 parse_pdf 的返回值可避免重复 OCR（OCR 较慢）

    Returns:
        合并后的纯文本
    """
    if pages is None:
        pages = parse_pdf(path_or_bytes, ocr_fallback=ocr_fallback)

    # 跳过封面/空页，只保留有内容的页；不拼页标记，保持纯文本方便下游结构解析
    parts = [p["text"] for p in pages if p["source"] != "empty" and p["text"].strip()]
    return "\n\n".join(parts)
