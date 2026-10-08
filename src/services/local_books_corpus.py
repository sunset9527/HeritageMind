"""Build a local, traceable retrieval corpus from copyright-restricted heritage books.

The generated corpus deliberately lives outside version control.  It contains extracted
book text, while the repository only contains the repeatable builder and its schema.
"""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from html.parser import HTMLParser
import json
from pathlib import Path
import re
from tempfile import NamedTemporaryFile
from typing import Any, Callable, Iterable
from zipfile import ZipFile


SUPPORTED_BOOK_SUFFIXES = {".pdf", ".epub"}
_HEADING = re.compile(r"^\s*(第[一二三四五六七八九十百千万0-9]+[章节卷][^\n]{0,60})", re.MULTILINE)


class LocalBooksCorpusError(RuntimeError):
    """Raised when a corpus cannot safely be staged or activated."""


@dataclass(frozen=True)
class CorpusBuildResult:
    corpus_id: str
    source_count: int
    document_count: int
    empty_page_count: int


class _TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []

    def handle_data(self, data: str) -> None:
        self.parts.append(data)

    def text(self) -> str:
        return "\n".join(part.strip() for part in self.parts if part.strip())


def _sha256_file(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _parse_epub_sections(path: Path) -> list[dict[str, Any]]:
    """Read EPUB XHTML chapters without adding a new runtime dependency."""
    sections: list[dict[str, Any]] = []
    with ZipFile(path) as archive:
        names = sorted(
            name for name in archive.namelist()
            if name.lower().endswith((".xhtml", ".html", ".htm"))
        )
        for position, name in enumerate(names, start=1):
            parser = _TextExtractor()
            parser.feed(archive.read(name).decode("utf-8", errors="ignore"))
            text = parser.text()
            sections.append({
                "page": position,
                "text": text,
                "source": "text" if text else "empty",
                "char_count": len(text),
            })
    return sections


def _default_pdf_page_parser(path: Path, **kwargs: Any) -> list[dict[str, Any]]:
    from src.services.pdf_parser import parse_pdf

    return parse_pdf(path, **kwargs)


def _write_atomically(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False, newline="\n") as temporary:
        temporary.write(content)
        temporary_path = Path(temporary.name)
    temporary_path.replace(path)


def _split_text(text: str, chunk_chars: int) -> Iterable[str]:
    normalized = "\n".join(line.strip() for line in text.splitlines() if line.strip())
    while len(normalized) > chunk_chars:
        boundary = max(normalized.rfind("。", 0, chunk_chars), normalized.rfind("\n", 0, chunk_chars))
        if boundary < chunk_chars // 2:
            boundary = chunk_chars
        else:
            boundary += 1
        yield normalized[:boundary].strip()
        normalized = normalized[boundary:].strip()
    if normalized:
        yield normalized


class LocalBooksCorpusBuilder:
    """Stage deterministic retrieval documents for all PDF/EPUB files in a local folder."""

    def __init__(
        self,
        library_path: Path | str,
        output_path: Path | str,
        *,
        pdf_page_parser: Callable[..., list[dict[str, Any]]] | None = None,
        chunk_chars: int = 1200,
    ) -> None:
        if chunk_chars < 100:
            raise ValueError("chunk_chars must be at least 100")
        self.library_path = Path(library_path)
        self.output_path = Path(output_path)
        self.pdf_page_parser = pdf_page_parser or _default_pdf_page_parser
        self.chunk_chars = chunk_chars

    def build(self, *, corpus_id: str = "heritage-books-v1", dry_run: bool = False) -> CorpusBuildResult:
        sources = self._discover_sources()

        documents: list[dict[str, Any]] = []
        source_catalog: list[dict[str, Any]] = []
        empty_page_count = 0
        for source_path in sources:
            source_hash = _sha256_file(source_path)
            pages = self._read_pages(source_path)
            source_catalog.append({
                "source_id": f"book:{source_hash}",
                "book_title": source_path.stem,
                "format": source_path.suffix.lower().lstrip("."),
                "size_bytes": source_path.stat().st_size,
                "sha256": source_hash,
            })
            chapter_title = ""
            for page in pages:
                text = str(page.get("text", "")).strip()
                if not text:
                    empty_page_count += 1
                    continue
                heading = _HEADING.search(text)
                if heading:
                    chapter_title = heading.group(1).strip()
                page_number = int(page["page"])
                extraction_method = str(page.get("source", "text"))
                for chunk_index, chunk in enumerate(_split_text(text, self.chunk_chars), start=1):
                    document_id = f"book:{source_hash[:16]}:p{page_number}:c{chunk_index}"
                    documents.append({
                        "id": document_id,
                        "content": chunk,
                        "char_count": len(chunk),
                        "metadata": {
                            "corpus_id": corpus_id,
                            "source_id": f"book:{source_hash}",
                            "book_title": source_path.stem,
                            "chapter_title": chapter_title,
                            "page_start": page_number,
                            "page_end": page_number,
                            "extraction_method": extraction_method,
                            "content_sha256": sha256(chunk.encode("utf-8")).hexdigest(),
                        },
                    })
        if not documents:
            raise LocalBooksCorpusError("没有可发布的文字片段；请检查 PDF 文字层或 OCR 配置")

        result = CorpusBuildResult(corpus_id, len(sources), len(documents), empty_page_count)
        if dry_run:
            return result
        catalog = {
            "corpus_id": corpus_id,
            "status": "staged",
            "source_count": result.source_count,
            "document_count": result.document_count,
            "empty_page_count": result.empty_page_count,
            "sources": source_catalog,
        }
        _write_atomically(self.output_path / "documents.jsonl", "".join(
            json.dumps(document, ensure_ascii=False, sort_keys=True) + "\n" for document in documents
        ))
        _write_atomically(self.output_path / "catalog.json", json.dumps(catalog, ensure_ascii=False, indent=2, sort_keys=True) + "\n")
        return result

    def preflight(self, *, corpus_id: str = "heritage-books-v1") -> CorpusBuildResult:
        """Check the local source folder without opening PDFs, EPUBs, or OCR models."""
        return CorpusBuildResult(corpus_id, len(self._discover_sources()), 0, 0)

    def _discover_sources(self) -> list[Path]:
        if not self.library_path.is_dir():
            raise LocalBooksCorpusError(f"知识库目录不存在：{self.library_path}")
        sources = sorted(
            (path for path in self.library_path.iterdir() if path.is_file() and path.suffix.lower() in SUPPORTED_BOOK_SUFFIXES),
            key=lambda path: path.name,
        )
        if not sources:
            raise LocalBooksCorpusError("知识库目录中没有 PDF 或 EPUB 文件")
        return sources

    def _read_pages(self, source_path: Path) -> list[dict[str, Any]]:
        if source_path.suffix.lower() == ".epub":
            return _parse_epub_sections(source_path)
        return self.pdf_page_parser(source_path, ocr_fallback=True)


def activate_staged_corpus(output_path: Path | str) -> None:
    """Mark a fully-built local corpus active without changing archived source files."""
    root = Path(output_path)
    catalog_path = root / "catalog.json"
    documents_path = root / "documents.jsonl"
    if not catalog_path.is_file() or not documents_path.is_file() or not documents_path.read_text(encoding="utf-8").strip():
        raise LocalBooksCorpusError("缺少完整 staged corpus，拒绝激活")
    catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
    if catalog.get("status") != "staged" or not catalog.get("corpus_id"):
        raise LocalBooksCorpusError("只有带 corpus_id 的 staged corpus 可以激活")
    catalog["status"] = "active"
    _write_atomically(catalog_path, json.dumps(catalog, ensure_ascii=False, indent=2, sort_keys=True) + "\n")
