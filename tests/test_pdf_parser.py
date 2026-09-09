# -*- coding: utf-8 -*-
"""
PDF 解析器测试（HeritageMind 版）：文本层 + RapidOCR 扫描页 OCR 双通道

可直接运行:  python tests/test_pdf_parser.py
或 pytest:   python -m pytest tests/test_pdf_parser.py -v

额外覆盖：
- parse_pdf 支持 bytes 输入（对接文档上传接口）
- document_parser.parse_document 接入验证（扫描件也能出文本）
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import fitz
import pytest

from src.services.pdf_parser import parse_pdf, parse_pdf_to_text

FIXTURES_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fixtures")
TEXT_PDF = os.path.join(FIXTURES_DIR, "sample_text_heritage.pdf")
SCANNED_PDF = os.path.join(FIXTURES_DIR, "sample_scanned_heritage.pdf")

# 非遗样本文本（文本型 PDF 用）
HERITAGE_SAMPLE = (
    "龙泉青瓷传统烧制技艺\n"
    "龙泉青瓷是中国传统制瓷珍品，始于三国两晋，盛于南宋，"
    "以釉色青翠、造型典雅著称，2009年入选联合国教科文组织人类非物质文化遗产代表作名录。"
)


def _find_cjk_font():
    """查找 Windows 中文字体，保证 PIL 渲染的图片能被 RapidOCR 识别"""
    for cand in [r"C:\Windows\Fonts\msyh.ttc", r"C:\Windows\Fonts\simhei.ttf",
                 r"C:\Windows\Fonts\simsun.ttc", r"C:\Windows\Fonts\Deng.ttf"]:
        if os.path.exists(cand):
            return cand
    return None


def _ensure_fixtures():
    """生成测试 PDF（仅首次）：文本型 + 扫描型，存到 tests/fixtures/"""
    os.makedirs(FIXTURES_DIR, exist_ok=True)

    # 1) 文本型 PDF：fitz 内置中文字体 china-s 写入文本层（无任何图片）
    if not os.path.exists(TEXT_PDF):
        doc = fitz.open()
        page = doc.new_page(width=595, height=842)
        page.insert_text((72, 72), HERITAGE_SAMPLE, fontname="china-s", fontsize=14)
        doc.save(TEXT_PDF)
        doc.close()
        print(f"[fixture] 已生成文本型 PDF: {TEXT_PDF}")

    # 2) 扫描型 PDF：PIL 把中文渲染成图片 → 插入为整页图片（无文本层）
    if not os.path.exists(SCANNED_PDF):
        from PIL import Image, ImageDraw, ImageFont
        font_path = _find_cjk_font()
        assert font_path, "未找到 Windows 中文字体，无法生成扫描测试件"
        img = Image.new("RGB", (1100, 320), "white")
        d = ImageDraw.Draw(img)
        font = ImageFont.truetype(font_path, 44)
        d.text((60, 130), "苏绣：以针代笔，以线为墨（扫描件样张）", font=font, fill="black")
        tmp_png = os.path.join(FIXTURES_DIR, "_scanned_tmp.png")
        img.save(tmp_png)
        doc = fitz.open()
        page = doc.new_page(width=595, height=842)
        page.insert_image(page.rect, filename=tmp_png)  # 整页图片 → 文本层为空
        doc.save(SCANNED_PDF)
        doc.close()
        os.remove(tmp_png)
        print(f"[fixture] 已生成扫描型 PDF: {SCANNED_PDF}")


def test_text_pdf_uses_text_layer():
    """文本型 PDF：全部走文本层，不触发 OCR"""
    _ensure_fixtures()
    pages = parse_pdf(TEXT_PDF)
    assert len(pages) == 1
    p = pages[0]
    assert p["source"] == "text"
    assert p["char_count"] > 0
    assert "龙泉青瓷" in p["text"]


def test_scanned_pdf_uses_ocr():
    """扫描型 PDF：无文本层 → 触发 RapidOCR，识别出中文"""
    _ensure_fixtures()
    pages = parse_pdf(SCANNED_PDF)
    assert len(pages) == 1
    p = pages[0]
    assert p["source"] == "ocr"
    assert p["char_count"] > 0
    assert "苏绣" in p["text"]


def test_parse_pdf_accepts_bytes():
    """bytes 输入：与文档上传接口（parse_document 收 bytes）一致"""
    _ensure_fixtures()
    with open(SCANNED_PDF, "rb") as f:
        data = f.read()
    pages = parse_pdf(data)
    assert pages[0]["source"] == "ocr"
    assert "苏绣" in pages[0]["text"]


def test_parse_document_integration():
    """document_parser.parse_document 接入验证：文本型 + 扫描型都能出文本"""
    _ensure_fixtures()
    from src.services.document_parser import parse_document

    with open(TEXT_PDF, "rb") as f:
        text = parse_document(f.read(), "sample_text_heritage.pdf", "application/pdf")
    assert "龙泉青瓷" in text

    with open(SCANNED_PDF, "rb") as f:
        text = parse_document(f.read(), "sample_scanned_heritage.pdf", "application/pdf")
    assert "苏绣" in text


if __name__ == "__main__":
    # 支持直接运行: python tests/test_pdf_parser.py
    test_text_pdf_uses_text_layer()
    print("[PASS] 文本型 PDF 全部走文本层，source=text")
    test_scanned_pdf_uses_ocr()
    print("[PASS] 扫描型 PDF 走 RapidOCR，source=ocr 且识别出中文")
    test_parse_pdf_accepts_bytes()
    print("[PASS] parse_pdf 支持 bytes 输入")
    test_parse_document_integration()
    print("[PASS] document_parser.parse_document 接入验证通过（文本+扫描双通道）")
    print("全部测试通过 ✔")
