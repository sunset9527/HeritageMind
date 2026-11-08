import logging
from pathlib import Path

from src.services.error_sanitizer import (
    SensitiveDataFilter,
    install_sensitive_logging_filter,
    public_error,
    redact_sensitive_text,
)


_SECRET = "sk-stage1-should-not-leak"
_DATABASE_URL = "mysql+pymysql://root:db-secret@db.internal:3306/heritagemind"
_WINDOWS_PATH = r"C:\\Users\\operator\\private\\source.txt"
_LINUX_PATH = "/srv/heritagemind/private/source.txt"


def test_public_errors_use_a_stable_message_instead_of_exception_text():
    error = RuntimeError(f"provider said {_SECRET} while reading {_WINDOWS_PATH}")

    result = public_error(error, request_id="request-123")

    assert result == {
        "error": {
            "code": "internal_error",
            "message": "服务暂时无法处理该请求，请稍后重试",
            "request_id": "request-123",
        }
    }
    assert _SECRET not in str(result)
    assert _WINDOWS_PATH not in str(result)


def test_redaction_removes_credentials_connection_urls_and_absolute_paths():
    raw = (
        f"Authorization: Bearer {_SECRET}; database={_DATABASE_URL}; "
        f"windows={_WINDOWS_PATH}; unix={_LINUX_PATH}; password=hunter2"
    )

    redacted = redact_sensitive_text(raw)

    for sensitive in (_SECRET, _DATABASE_URL, _WINDOWS_PATH, _LINUX_PATH, "hunter2"):
        assert sensitive not in redacted
    assert "[REDACTED" in redacted


def test_redaction_keeps_short_non_sensitive_context_for_admin_diagnosis():
    redacted = redact_sensitive_text("index refresh timed out after 15 seconds")

    assert redacted == "index refresh timed out after 15 seconds"


def test_logging_filter_redacts_message_and_structured_context():
    record = logging.LogRecord(
        "heritagemind.test",
        logging.ERROR,
        __file__,
        1,
        "provider failed: %s",
        (_SECRET,),
        None,
    )
    record.context = {"database": _DATABASE_URL, "path": _WINDOWS_PATH}

    assert SensitiveDataFilter().filter(record)
    assert _SECRET not in record.getMessage()
    assert _DATABASE_URL not in str(record.context)
    assert _WINDOWS_PATH not in str(record.context)


def test_logging_filter_is_added_once_to_each_existing_handler():
    logger = logging.getLogger("heritagemind.test.filter-install")
    handler = logging.NullHandler()
    logger.handlers = [handler]
    try:
        install_sensitive_logging_filter(logger)
        install_sensitive_logging_filter(logger)
        assert sum(isinstance(item, SensitiveDataFilter) for item in handler.filters) == 1
    finally:
        logger.handlers = []


def test_api_and_worker_entrypoints_install_the_sensitive_logging_filter():
    root = Path(__file__).resolve().parents[1]
    for relative_path in ("api.py", "src/workers/upload_worker.py"):
        assert "install_sensitive_logging_filter()" in (root / relative_path).read_text(encoding="utf-8")
