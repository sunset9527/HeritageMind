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
import os
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


def _default_pdf_page_reader(path: Path, *, start_page: int = 1):
    from src.services.pdf_parser import iter_pdf_pages

    return iter_pdf_pages(path, ocr_fallback=True, start_page=start_page)


def _default_pdf_page_counter(path: Path) -> int:
    import fitz

    with fitz.open(path) as document:
        return len(document)


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
        pdf_page_reader: Callable[..., Iterable[dict[str, Any]]] | None = None,
        pdf_page_counter: Callable[[Path], int] | None = None,
        chunk_chars: int = 1200,
    ) -> None:
        if chunk_chars < 100:
            raise ValueError("chunk_chars must be at least 100")
        self.library_path = Path(library_path)
        self.output_path = Path(output_path)
        self.pdf_page_parser = pdf_page_parser
        self.pdf_page_reader = pdf_page_reader or _default_pdf_page_reader
        self.pdf_page_counter = pdf_page_counter or _default_pdf_page_counter
        self.chunk_chars = chunk_chars

    def build(self, *, corpus_id: str = "heritage-books-v1", dry_run: bool = False) -> CorpusBuildResult:
        sources = self._discover_sources()

        source_catalog = [self._source_record(source) for source in sources]
        progress = self._load_or_start_progress(corpus_id, source_catalog)
        completed_units = set(progress["completed_units"])
        seen_document_ids = self._existing_document_ids()
        document_count = len(seen_document_ids)
        documents_path = self.output_path / "documents.jsonl"
        try:
            for source_path, source in zip(sources, source_catalog):
                source_id = source["source_id"]
                completed_pages = {
                    int(unit.rsplit(":p", 1)[1])
                    for unit in completed_units if unit.startswith(f"{source_id}:")
                }
                start_page = next((page for page in range(1, source["unit_count"] + 1) if page not in completed_pages), source["unit_count"] + 1)
                chapter_title = ""
                for page in self._read_pages(source_path, start_page=start_page):
                    page_number = int(page["page"])
                    unit_key = f"{source_id}:p{page_number}"
                    if unit_key in completed_units:
                        continue
                    progress["current_unit"] = {"book_title": source["book_title"], "page": page_number}
                    text = str(page.get("text", "")).strip()
                    if not text:
                        progress["empty_page_count"] += 1
                    else:
                        heading = _HEADING.search(text)
                        if heading:
                            chapter_title = heading.group(1).strip()
                        extraction_method = str(page.get("source", "text"))
                        for chunk_index, chunk in enumerate(_split_text(text, self.chunk_chars), start=1):
                            document_id = f"book:{source['sha256'][:16]}:p{page_number}:c{chunk_index}"
                            if document_id in seen_document_ids:
                                continue
                            document = {
                                "id": document_id,
                                "content": chunk,
                                "char_count": len(chunk),
                                "metadata": {
                                    "corpus_id": corpus_id,
                                    "source_id": source_id,
                                    "book_title": source["book_title"],
                                    "chapter_title": chapter_title,
                                    "page_start": page_number,
                                    "page_end": page_number,
                                    "extraction_method": extraction_method,
                                    "content_sha256": sha256(chunk.encode("utf-8")).hexdigest(),
                                },
                            }
                            self._append_document(documents_path, document)
                            seen_document_ids.add(document_id)
                            document_count += 1
                    completed_units.add(unit_key)
                    progress["completed_units"] = sorted(completed_units)
                    progress["completed_unit_count"] = len(completed_units)
                    progress["percent"] = round(100 * len(completed_units) / progress["total_unit_count"], 2)
                    self._write_progress(progress)
        except Exception as error:
            progress["status"] = "incomplete"
            progress["error"] = str(error)
            self._write_progress(progress)
            raise
        if not document_count:
            raise LocalBooksCorpusError("没有可发布的文字片段；请检查 PDF 文字层或 OCR 配置")
        progress.update({"status": "complete", "current_unit": None, "percent": 100.0, "error": ""})
        self._write_progress(progress)
        result = CorpusBuildResult(corpus_id, len(sources), document_count, progress["empty_page_count"])
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

    def _source_record(self, source_path: Path) -> dict[str, Any]:
        source_hash = _sha256_file(source_path)
        if source_path.suffix.lower() == ".pdf":
            unit_count = len(self.pdf_page_parser(source_path, ocr_fallback=True)) if self.pdf_page_parser else self.pdf_page_counter(source_path)
        else:
            unit_count = len(_parse_epub_sections(source_path))
        return {"source_id": f"book:{source_hash}", "book_title": source_path.stem,
                "format": source_path.suffix.lower().lstrip("."), "size_bytes": source_path.stat().st_size,
                "sha256": source_hash, "unit_count": unit_count}

    def _load_or_start_progress(self, corpus_id: str, sources: list[dict[str, Any]]) -> dict[str, Any]:
        path = self.output_path / "progress.json"
        signature = [[source["source_id"], source["unit_count"]] for source in sources]
        if path.is_file():
            progress = json.loads(path.read_text(encoding="utf-8"))
            if progress.get("corpus_id") != corpus_id or progress.get("source_signature") != signature:
                raise LocalBooksCorpusError("现有进度与当前图书不一致；请使用新的输出目录")
            progress["status"] = "running"
            return progress
        progress = {"corpus_id": corpus_id, "status": "running", "source_signature": signature,
                    "total_unit_count": sum(source["unit_count"] for source in sources), "completed_unit_count": 0,
                    "completed_units": [], "empty_page_count": 0, "percent": 0.0, "current_unit": None, "error": ""}
        self._write_progress(progress)
        return progress

    def _existing_document_ids(self) -> set[str]:
        path = self.output_path / "documents.jsonl"
        if not path.is_file():
            return set()
        return {json.loads(line)["id"] for line in path.read_text(encoding="utf-8").splitlines() if line.strip()}

    @staticmethod
    def _append_document(path: Path, document: dict[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8", newline="\n") as handle:
            handle.write(json.dumps(document, ensure_ascii=False, sort_keys=True) + "\n")
            handle.flush()
            os.fsync(handle.fileno())

    def _write_progress(self, progress: dict[str, Any]) -> None:
        _write_atomically(self.output_path / "progress.json", json.dumps(progress, ensure_ascii=False, indent=2, sort_keys=True) + "\n")

    def _read_pages(self, source_path: Path, *, start_page: int) -> Iterable[dict[str, Any]]:
        if source_path.suffix.lower() == ".epub":
            return _parse_epub_sections(source_path)[start_page - 1:]
        if self.pdf_page_parser is not None:
            return self.pdf_page_parser(source_path, ocr_fallback=True)[start_page - 1:]
        return self.pdf_page_reader(source_path, start_page=start_page)


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
