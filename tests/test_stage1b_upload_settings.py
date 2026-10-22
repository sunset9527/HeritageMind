"""阶段 1B 上传与后台任务的默认资源预算。"""

import pytest
from pydantic import ValidationError

from config import Settings


def test_stage1b_upload_limits_have_safe_defaults():
    settings = Settings(_env_file=None)

    assert settings.upload_request_max_bytes == 52 * 1024 * 1024
    assert settings.image_upload_max_bytes == 10 * 1024 * 1024
    assert settings.similar_image_max_bytes == 10 * 1024 * 1024
    assert settings.audio_upload_max_bytes == 50 * 1024 * 1024
    assert settings.pdf_upload_max_bytes == 25 * 1024 * 1024
    assert settings.docx_upload_max_bytes == 15 * 1024 * 1024
    assert settings.text_upload_max_bytes == 2 * 1024 * 1024


def test_stage1b_processing_limits_have_safe_defaults():
    settings = Settings(_env_file=None)

    assert settings.pdf_max_pages == 100
    assert settings.pdf_max_ocr_pages == 25
    assert settings.document_max_chars == 500_000
    assert settings.document_task_timeout_seconds == 180
    assert settings.audio_max_duration_seconds == 30 * 60
    assert settings.audio_task_timeout_seconds == 20 * 60
    assert settings.upload_task_max_attempts == 3
    assert settings.index_max_documents == 1_000
    assert settings.index_max_total_chars == 5_000_000
    assert settings.index_task_timeout_seconds == 10 * 60


def test_stage1b_storage_roots_are_explicit_and_separate_from_corpus():
    settings = Settings(_env_file=None)

    assert settings.media_storage_path == "./data/media"
    assert settings.document_upload_path == "./data/uploads/documents"
    assert settings.index_versions_path == "./data/index_versions"
    assert settings.document_upload_path != settings.crafts_doc_path


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("image_upload_max_bytes", 0),
        ("pdf_max_pages", 0),
        ("document_task_timeout_seconds", 0),
        ("upload_task_max_attempts", 0),
    ],
)
def test_stage1b_resource_limits_reject_non_positive_values(field: str, value: int):
    with pytest.raises(ValidationError):
        Settings(_env_file=None, **{field: value})
