"""上传 worker 的文档处理器；父进程拥有状态迁移和产物发布权。"""

from __future__ import annotations

import asyncio
import os
import time
from pathlib import Path

from config import settings
from src.database import SessionLocal
from src.models.upload import DocumentUpload, ProcessingStatus
from src.services.document_parser import ParsedDocument, parse_document_path
from src.services.task_state import claim_document, utcnow_naive
from src.services.upload_security import resolve_under
from src.workers.isolated_runner import (
    IsolatedProcessError,
    IsolatedProcessTimeout,
    run_isolated,
)


def parse_document_subprocess(
    path: str,
    format_name: str,
    max_chars: int,
    max_pdf_pages: int,
    max_ocr_pages: int,
    timeout_seconds: int,
) -> ParsedDocument:
    return parse_document_path(
        path,
        format_name,
        max_chars=max_chars,
        max_pdf_pages=max_pdf_pages,
        max_ocr_pages=max_ocr_pages,
        deadline=time.monotonic() + timeout_seconds,
    )


async def process_document_job(
    document_id: int,
    *,
    db=None,
    storage_root: Path | str | None = None,
) -> str:
    owns_session = db is None
    session = db or SessionLocal()
    root = Path(storage_root or settings.document_upload_path)
    part_path: Path | None = None
    final_path: Path | None = None
    published = False
    try:
        if not claim_document(
            session, document_id, max_attempts=settings.upload_task_max_attempts
        ):
            return "not_claimed"
        row = session.get(DocumentUpload, document_id)
        if row is None:
            return "not_found"
        source_path = resolve_under(root, row.storage_name)
        if not source_path.exists():
            raise FileNotFoundError("上传原件不存在")

        result = await asyncio.to_thread(
            run_isolated,
            "src.workers.processors:parse_document_subprocess",
            args=(
                str(source_path),
                row.extension.lstrip(".").lower(),
                settings.document_max_chars,
                settings.pdf_max_pages,
                settings.pdf_max_ocr_pages,
                settings.document_task_timeout_seconds,
            ),
            timeout_seconds=settings.document_task_timeout_seconds,
        )
        if not isinstance(result, ParsedDocument) or not result.text.strip():
            raise RuntimeError("文档未提取到有效正文")

        parsed_name = f"{Path(row.storage_name).stem}.parsed.txt"
        final_path = resolve_under(root, parsed_name)
        part_path = resolve_under(root, parsed_name + ".part")
        with part_path.open("x", encoding="utf-8") as output:
            output.write(result.text)
        os.replace(part_path, final_path)
        published = True

        row.parsed_storage_name = parsed_name
        row.char_count = result.char_count
        row.page_count = result.page_count
        row.ocr_page_count = result.ocr_page_count
        row.processing_status = ProcessingStatus.READY.value
        row.error_code = None
        row.error_message = None
        row.finished_at = utcnow_naive()
        session.commit()
        return "ready"
    except Exception as exc:
        session.rollback()
        if part_path is not None:
            part_path.unlink(missing_ok=True)
        if published and final_path is not None:
            final_path.unlink(missing_ok=True)
        row = session.get(DocumentUpload, document_id)
        if row is not None:
            row.processing_status = ProcessingStatus.FAILED.value
            if isinstance(exc, IsolatedProcessTimeout):
                row.error_code = "timeout"
            elif isinstance(exc, IsolatedProcessError):
                row.error_code = "processing_error"
            elif isinstance(exc, FileNotFoundError):
                row.error_code = "file_missing"
            else:
                row.error_code = getattr(exc, "code", "processing_error")
            row.error_message = str(exc)[:1000]
            row.finished_at = utcnow_naive()
            session.commit()
        return "failed"
    finally:
        if owns_session:
            session.close()
