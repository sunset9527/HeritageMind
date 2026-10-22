"""文档解析的页数、OCR、字符数与 deadline 边界。"""

import time
import zipfile

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.database import Base
from src.models.upload import DocumentUpload


def test_utf8_text_is_parsed_with_metadata(tmp_path):
    from src.services.document_parser import parse_document_path

    path = tmp_path / "note.txt"
    path.write_text("景泰蓝\n掐丝工艺", encoding="utf-8")
    result = parse_document_path(path, "txt", max_chars=100, deadline=time.monotonic() + 2)

    assert "掐丝" in result.text
    assert result.char_count == len(result.text)
    assert result.page_count == 0


def test_text_character_limit_and_expired_deadline_fail_closed(tmp_path):
    from src.services.document_parser import DocumentProcessingError, parse_document_path

    path = tmp_path / "note.md"
    path.write_text("abcdef", encoding="utf-8")
    with pytest.raises(DocumentProcessingError) as chars:
        parse_document_path(path, "md", max_chars=5, deadline=time.monotonic() + 2)
    assert chars.value.code == "character_limit_exceeded"

    with pytest.raises(DocumentProcessingError) as deadline:
        parse_document_path(path, "md", max_chars=100, deadline=time.monotonic() - 1)
    assert deadline.value.code == "deadline_exceeded"


def test_docx_reads_only_bounded_paragraph_text(tmp_path):
    from src.services.document_parser import parse_document_path

    path = tmp_path / "note.docx"
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("[Content_Types].xml", "<Types/>")
        archive.writestr("_rels/.rels", "<Relationships/>")
        archive.writestr(
            "word/document.xml",
            '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
            "<w:body><w:p><w:r><w:t>苏绣针法</w:t></w:r></w:p></w:body></w:document>",
        )
    result = parse_document_path(path, "docx", max_chars=100, deadline=time.monotonic() + 2)
    assert result.text == "苏绣针法"


def test_pdf_page_limit_is_checked_before_ocr(tmp_path):
    fitz = pytest.importorskip("fitz")
    from src.services.document_parser import DocumentProcessingError, parse_document_path

    path = tmp_path / "many.pdf"
    document = fitz.open()
    document.new_page()
    document.new_page()
    document.save(path)
    document.close()

    with pytest.raises(DocumentProcessingError) as error:
        parse_document_path(
            path,
            "pdf",
            max_chars=100,
            max_pdf_pages=1,
            max_ocr_pages=1,
            deadline=time.monotonic() + 2,
        )
    assert error.value.code == "pdf_page_limit_exceeded"


def test_worker_publishes_parsed_text_only_after_complete_success(tmp_path, monkeypatch):
    import asyncio
    import src.workers.processors as processors

    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    db = sessionmaker(bind=engine)()
    original = tmp_path / "source.txt"
    original.write_text("景泰蓝工艺", encoding="utf-8")
    row = DocumentUpload(
        craft_id="jingtailan",
        craft_name="景泰蓝",
        storage_name=original.name,
        original_name="资料.txt",
        extension=".txt",
        mime_type="text/plain",
        size_bytes=original.stat().st_size,
        content_sha256="a" * 64,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    monkeypatch.setattr(
        processors,
        "run_isolated",
        lambda target, args, timeout_seconds: processors.parse_document_subprocess(*args),
    )
    try:
        result = asyncio.run(processors.process_document_job(row.id, db=db, storage_root=tmp_path))
        db.refresh(row)
        assert result == "ready"
        assert row.processing_status == "ready"
        assert row.parsed_storage_name.endswith(".parsed.txt")
        assert (tmp_path / row.parsed_storage_name).read_text(encoding="utf-8") == "景泰蓝工艺"
        assert list(tmp_path.glob("*.part")) == []
    finally:
        db.close()
        engine.dispose()
