"""Helpers for keeping secrets and deployment details out of public errors."""

from __future__ import annotations

import logging
import re
from typing import Any


_PATTERNS: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"(?i)(?:mysql|postgres(?:ql)?|sqlite)(?:\+[\w-]+)?://[^\s'\";]+"), "[REDACTED_DATABASE_URL]"),
    (re.compile(r"(?i)(?:authorization\s*[:=]\s*)?bearer\s+[\w.\-~+/=]+"), "[REDACTED_TOKEN]"),
    (re.compile(r"(?i)(?:x-api-key|api[_ -]?key|password|secret)\s*[:=]\s*[^\s;,]+"), "[REDACTED_SECRET]"),
    (re.compile(r"\bsk-[A-Za-z0-9_-]+\b"), "[REDACTED_SECRET]"),
    (re.compile(r"(?<![\w:])[A-Za-z]:\\(?:[^\\\s]+\\)*[^\\\s]*"), "[REDACTED_PATH]"),
    (re.compile(r"(?<![\w:])/(?:[^\s/]+/)+[^\s/]*"), "[REDACTED_PATH]"),
)


def redact_sensitive_text(value: Any, *, max_length: int = 500) -> str:
    """Return a bounded diagnostic summary with common sensitive values removed."""
    result = str(value)
    for pattern, replacement in _PATTERNS:
        result = pattern.sub(replacement, result)
    return result[:max_length]


def _redact_log_value(value: Any) -> Any:
    if isinstance(value, str):
        return redact_sensitive_text(value)
    if isinstance(value, dict):
        return {key: _redact_log_value(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_redact_log_value(item) for item in value]
    if isinstance(value, tuple):
        return tuple(_redact_log_value(item) for item in value)
    return value


class SensitiveDataFilter(logging.Filter):
    """Remove secrets and deployment paths before a record reaches a handler."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.msg = redact_sensitive_text(record.getMessage())
        record.args = ()
        for key, value in tuple(record.__dict__.items()):
            if key not in {"msg", "args"}:
                record.__dict__[key] = _redact_log_value(value)
        return True


def install_sensitive_logging_filter(logger: logging.Logger | None = None) -> None:
    """Attach one sanitizing filter to every handler already configured on a logger."""
    target = logger or logging.getLogger()
    for handler in target.handlers:
        if not any(isinstance(item, SensitiveDataFilter) for item in handler.filters):
            handler.addFilter(SensitiveDataFilter())


def public_error(_exception: BaseException, *, request_id: str | None = None) -> dict[str, dict[str, str]]:
    """Build the stable public error envelope without inspecting exception text."""
    payload = {
        "code": "internal_error",
        "message": "服务暂时无法处理该请求，请稍后重试",
    }
    if request_id:
        payload["request_id"] = request_id
    return {"error": payload}
