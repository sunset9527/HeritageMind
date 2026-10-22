"""文档解析服务 — 支持 PDF / Word / Markdown / TXT（PDF 含扫描件 OCR 兜底）"""
import io
import logging
import time
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Optional
from xml.etree import ElementTree

from config import settings

logger = logging.getLogger(__name__)

ALLOWED_TYPES = {
    "text/plain": "txt",
    "text/markdown": "md",
    "text/x-markdown": "md",
    "application/pdf": "pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "docx",
}


class DocumentProcessingError(RuntimeError):
    def __init__(self, code: str, detail: str):
        super().__init__(detail)
        self.code = code
        self.detail = detail


@dataclass(frozen=True)
class ParsedDocument:
    text: str
    char_count: int
    page_count: int = 0
    ocr_page_count: int = 0


def _check_deadline(deadline: float) -> None:
    if time.monotonic() >= deadline:
        raise DocumentProcessingError("deadline_exceeded", "文档解析超过截止时间")


def _bounded_text(text: str, max_chars: int) -> str:
    normalized = text.strip()
    if len(normalized) > max_chars:
        raise DocumentProcessingError("character_limit_exceeded", "文档提取字符数超限")
    return normalized


def _parse_text_path(path: Path, max_chars: int, deadline: float) -> ParsedDocument:
    decoder_parts: list[str] = []
    count = 0
    try:
        with path.open("r", encoding="utf-8", errors="strict") as source:
            while True:
                _check_deadline(deadline)
                chunk = source.read(64 * 1024)
                if not chunk:
                    break
                if "\x00" in chunk:
                    raise DocumentProcessingError("invalid_text", "文本包含 NUL 字节")
                count += len(chunk)
                if count > max_chars:
                    raise DocumentProcessingError(
                        "character_limit_exceeded", "文档提取字符数超限"
                    )
                decoder_parts.append(chunk)
    except UnicodeDecodeError as exc:
        raise DocumentProcessingError("invalid_text", "文本不是有效 UTF-8") from exc
    text = _bounded_text("".join(decoder_parts), max_chars)
    return ParsedDocument(text=text, char_count=len(text))


def _parse_docx_path(path: Path, max_chars: int, deadline: float) -> ParsedDocument:
    paragraphs: list[str] = []
    current: list[str] = []
    total = 0
    try:
        with zipfile.ZipFile(path) as archive, archive.open("word/document.xml") as source:
            for _, element in ElementTree.iterparse(source, events=("end",)):
                _check_deadline(deadline)
                tag = element.tag.rsplit("}", 1)[-1]
                if tag == "t" and element.text:
                    current.append(element.text)
                    total += len(element.text)
                    if total > max_chars:
                        raise DocumentProcessingError(
                            "character_limit_exceeded", "文档提取字符数超限"
                        )
                elif tag == "p":
                    paragraph = "".join(current).strip()
                    if paragraph:
                        paragraphs.append(paragraph)
                    current.clear()
                element.clear()
    except (KeyError, zipfile.BadZipFile, ElementTree.ParseError) as exc:
        raise DocumentProcessingError("invalid_docx", "DOCX 正文结构无效") from exc
    text = _bounded_text("\n".join(paragraphs), max_chars)
    return ParsedDocument(text=text, char_count=len(text))


def _parse_pdf_path(
    path: Path,
    max_chars: int,
    max_pdf_pages: int,
    max_ocr_pages: int,
    deadline: float,
) -> ParsedDocument:
    try:
        import fitz
    except ImportError as exc:
        raise DocumentProcessingError("dependency_missing", "PDF 解析依赖未安装") from exc

    document = fitz.open(str(path))
    try:
        page_count = len(document)
        if page_count > max_pdf_pages:
            raise DocumentProcessingError("pdf_page_limit_exceeded", "PDF 页数超限")
        parts: list[str] = []
        char_count = 0
        ocr_count = 0
        for page in document:
            _check_deadline(deadline)
            text = (page.get_text("text") or "").strip()
            if len(text) < 20:
                ocr_count += 1
                if ocr_count > max_ocr_pages:
                    raise DocumentProcessingError("ocr_page_limit_exceeded", "PDF OCR 页数超限")
                width = int(page.rect.width / 72 * 200)
                height = int(page.rect.height / 72 * 200)
                if width * height > settings.image_max_pixels:
                    raise DocumentProcessingError("render_pixel_limit_exceeded", "PDF 页面渲染像素超限")
                _check_deadline(deadline)
                from src.services.pdf_parser import _ocr_page

                text = (_ocr_page(page) or "").strip()
            if text:
                char_count += len(text)
                if char_count > max_chars:
                    raise DocumentProcessingError(
                        "character_limit_exceeded", "文档提取字符数超限"
                    )
                parts.append(text)
        merged = "\n\n".join(parts)
        return ParsedDocument(
            text=merged,
            char_count=len(merged),
            page_count=page_count,
            ocr_page_count=ocr_count,
        )
    finally:
        document.close()


def parse_document_path(
    path: str | Path,
    format_name: str,
    *,
    max_chars: int = settings.document_max_chars,
    max_pdf_pages: int = settings.pdf_max_pages,
    max_ocr_pages: int = settings.pdf_max_ocr_pages,
    deadline: float,
) -> ParsedDocument:
    source = Path(path)
    _check_deadline(deadline)
    if format_name in {"txt", "md"}:
        return _parse_text_path(source, max_chars, deadline)
    if format_name == "docx":
        return _parse_docx_path(source, max_chars, deadline)
    if format_name == "pdf":
        return _parse_pdf_path(
            source, max_chars, max_pdf_pages, max_ocr_pages, deadline
        )
    raise DocumentProcessingError("unsupported_file_type", "不支持的文档格式")


def parse_document(file_bytes: bytes, filename: str, mime_type: str) -> Optional[str]:
    """解析文档内容，返回纯文本"""
    ext = Path(filename).suffix.lower()

    if mime_type == "application/pdf" or ext == ".pdf":
        return _parse_pdf(file_bytes)
    elif mime_type.endswith("wordprocessingml.document") or ext == ".docx":
        return _parse_docx(file_bytes)
    elif "markdown" in mime_type or ext in (".md", ".markdown"):
        return _parse_markdown(file_bytes)
    elif "text" in mime_type or ext == ".txt":
        return _parse_txt(file_bytes)

    logger.warning(f"不支持的文件类型: {mime_type} ({filename})")
    return None


def _parse_pdf(data: bytes) -> str:
    """解析 PDF：优先 pymupdf 文本层 + RapidOCR 扫描页 OCR 兜底，pdfplumber 作为最后回退"""
    # 第一优先：本项目的 PDF 解析器（文本层 + RapidOCR 扫描页 OCR）
    try:
        from src.services.pdf_parser import parse_pdf_to_text
        return parse_pdf_to_text(data)
    except ImportError:
        pass  # pdf_parser 不存在时回退到 pdfplumber
    except Exception as e:
        logger.warning(f"pymupdf/RapidOCR 解析 PDF 失败，回退 pdfplumber: {e}")

    # 回退：pdfplumber 仅文本层（无 OCR 能力）
    try:
        import pdfplumber
        text = []
        with pdfplumber.open(io.BytesIO(data)) as pdf:
            for page in pdf.pages:
                t = page.extract_text()
                if t:
                    text.append(t)
        return "\n\n".join(text)
    except ImportError:
        return "（pdfplumber 未安装）"
    except Exception as e:
        logger.warning(f"PDF 解析失败: {e}")
        return ""


def _parse_docx(data: bytes) -> str:
    try:
        from docx import Document
        doc = Document(io.BytesIO(data))
        return "\n".join(p.text for p in doc.paragraphs if p.text.strip())
    except ImportError:
        return "（python-docx 未安装）"
    except Exception as e:
        logger.warning(f"Word 解析失败: {e}")
        return ""


def _parse_markdown(data: bytes) -> str:
    try:
        text = data.decode("utf-8")
        import markdown
        # 转换为纯文本（去掉 HTML 标签）
        html = markdown.markdown(text)
        import re
        clean = re.sub(r'<[^>]+>', '', html)
        return clean.strip()
    except Exception:
        return data.decode("utf-8", errors="ignore")


def _parse_txt(data: bytes) -> str:
    return data.decode("utf-8", errors="ignore")
