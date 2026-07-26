"""文档解析服务 — 支持 PDF / Word / Markdown / TXT"""
import io
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

ALLOWED_TYPES = {
    "text/plain": "txt",
    "text/markdown": "md",
    "text/x-markdown": "md",
    "application/pdf": "pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "docx",
}


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
