"""上传入口的文件名、类型、分块落盘与解压边界。"""

import asyncio
import hashlib
import io
import zipfile

import pytest
from starlette.datastructures import Headers, UploadFile


def _upload(data: bytes, filename: str, mime_type: str) -> UploadFile:
    return UploadFile(
        file=io.BytesIO(data),
        filename=filename,
        headers=Headers({"content-type": mime_type}),
    )


def _png(width: int = 1, height: int = 1) -> bytes:
    from PIL import Image

    output = io.BytesIO()
    Image.new("RGB", (width, height), "white").save(output, format="PNG")
    return output.getvalue()


def _docx(files: dict[str, bytes]) -> bytes:
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as archive:
        for name, content in files.items():
            archive.writestr(name, content)
    return output.getvalue()


@pytest.mark.parametrize(
    "filename",
    [
        "../secret.pdf",
        "..\\secret.pdf",
        "/etc/passwd",
        "C:\\temp\\clip.mp3",
        "folder/photo.png",
        "folder\\photo.png",
        "bad\x00name.txt",
        "a" * 256 + ".txt",
        "",
    ],
)
def test_original_filename_rejects_paths_controls_and_oversize(filename: str):
    from src.services.upload_security import UploadValidationError, validate_original_filename

    with pytest.raises(UploadValidationError) as exc_info:
        validate_original_filename(filename)

    assert exc_info.value.status_code == 400
    assert exc_info.value.code == "invalid_filename"


def test_original_filename_keeps_a_safe_unicode_display_name():
    from src.services.upload_security import validate_original_filename

    assert validate_original_filename(" 景泰蓝工艺说明.pdf ") == "景泰蓝工艺说明.pdf"


@pytest.mark.parametrize(
    ("data", "filename", "mime_type", "expected_format"),
    [
        (b"\xff\xd8\xff\xe0rest", "photo.jpg", "image/jpeg", "jpeg"),
        (b"\x89PNG\r\n\x1a\nrest", "photo.png", "image/png", "png"),
        (b"RIFF\x04\x00\x00\x00WEBPrest", "photo.webp", "image/webp", "webp"),
        (b"ID3\x04\x00\x00rest", "voice.mp3", "audio/mpeg", "mp3"),
        (b"RIFF\x04\x00\x00\x00WAVErest", "voice.wav", "audio/x-wav", "wav"),
        (b"\x00\x00\x00\x18ftypM4A rest", "voice.m4a", "audio/mp4", "m4a"),
        (b"fLaCrest", "voice.flac", "audio/flac", "flac"),
        (b"OggSrest", "voice.ogg", "audio/ogg", "ogg"),
        (b"%PDF-1.7\n", "notes.pdf", "application/pdf", "pdf"),
    ],
)
def test_binary_identity_requires_matching_extension_mime_and_signature(
    data: bytes,
    filename: str,
    mime_type: str,
    expected_format: str,
):
    from src.services.upload_security import validate_file_identity

    detected = validate_file_identity(filename, mime_type, data)

    assert detected.format == expected_format
    assert detected.extension == "." + expected_format.replace("jpeg", "jpg")


@pytest.mark.parametrize(
    ("filename", "mime_type", "data"),
    [
        ("photo.jpg", "image/jpeg", b"\x89PNG\r\n\x1a\nrest"),
        ("photo.png", "image/jpeg", b"\x89PNG\r\n\x1a\nrest"),
        ("notes.pdf", "application/pdf", b"not-a-pdf"),
        ("payload.svg", "image/svg+xml", b"<svg></svg>"),
        ("legacy.doc", "application/msword", b"\xd0\xcf\x11\xe0"),
    ],
)
def test_file_identity_rejects_disagreement_or_unsupported_formats(filename, mime_type, data):
    from src.services.upload_security import UploadValidationError, validate_file_identity

    with pytest.raises(UploadValidationError) as exc_info:
        validate_file_identity(filename, mime_type, data)

    assert exc_info.value.status_code == 415


def test_stream_upload_uses_chunks_hashes_content_and_keeps_internal_name(tmp_path):
    from src.services.upload_security import UploadPolicy, stage_upload

    data = _png()
    staged = asyncio.run(
        stage_upload(
            _upload(data, "非遗图片.png", "image/png"),
            tmp_path,
            UploadPolicy(formats=frozenset({"png"}), max_bytes=len(data), chunk_bytes=7),
        )
    )

    assert staged.original_name == "非遗图片.png"
    assert staged.size_bytes == len(data)
    assert staged.content_sha256 == hashlib.sha256(data).hexdigest()
    assert staged.storage_name.endswith(".png")
    assert "非遗图片" not in staged.storage_name
    assert staged.temp_path.name == staged.storage_name + ".part"
    assert staged.temp_path.read_bytes() == data


def test_stream_upload_removes_partial_file_when_late_chunk_exceeds_limit(tmp_path):
    from src.services.upload_security import UploadPolicy, UploadValidationError, stage_upload

    data = _png()
    with pytest.raises(UploadValidationError) as exc_info:
        asyncio.run(
            stage_upload(
                _upload(data, "photo.png", "image/png"),
                tmp_path,
                UploadPolicy(formats=frozenset({"png"}), max_bytes=len(data) - 1, chunk_bytes=5),
            )
        )

    assert exc_info.value.status_code == 413
    assert list(tmp_path.iterdir()) == []


def test_resolve_under_rejects_escape_even_for_internal_callers(tmp_path):
    from src.services.upload_security import UploadValidationError, resolve_under

    assert resolve_under(tmp_path, "safe-id.png").parent == tmp_path.resolve()
    with pytest.raises(UploadValidationError):
        resolve_under(tmp_path, "../escape.png")


def test_image_validation_rejects_pixel_budget(tmp_path):
    from src.services.upload_security import UploadValidationError, validate_image_file

    path = tmp_path / "large.png"
    path.write_bytes(_png(20, 20))

    with pytest.raises(UploadValidationError) as exc_info:
        validate_image_file(path, max_dimension=100, max_pixels=399)

    assert exc_info.value.code == "image_dimensions_exceeded"


def test_docx_validation_requires_members_and_limits_uncompressed_bytes(tmp_path):
    from src.services.upload_security import UploadValidationError, validate_docx_archive

    valid = tmp_path / "valid.docx"
    valid.write_bytes(_docx({
        "[Content_Types].xml": b"types",
        "_rels/.rels": b"rels",
        "word/document.xml": b"<w:document />",
    }))
    validate_docx_archive(valid, max_members=10, max_uncompressed_bytes=100, max_ratio=20)

    missing = tmp_path / "missing.docx"
    missing.write_bytes(_docx({"word/document.xml": b"<w:document />"}))
    with pytest.raises(UploadValidationError):
        validate_docx_archive(missing, max_members=10, max_uncompressed_bytes=100, max_ratio=20)

    expanded = tmp_path / "expanded.docx"
    expanded.write_bytes(_docx({
        "[Content_Types].xml": b"types",
        "_rels/.rels": b"rels",
        "word/document.xml": b"x" * 200,
    }))
    with pytest.raises(UploadValidationError) as exc_info:
        validate_docx_archive(expanded, max_members=10, max_uncompressed_bytes=100, max_ratio=200)
    assert exc_info.value.code == "archive_limits_exceeded"


@pytest.mark.parametrize("extension,mime_type", [(".txt", "text/plain"), (".md", "text/markdown")])
def test_text_identity_requires_utf8_without_nul(tmp_path, extension: str, mime_type: str):
    from src.services.upload_security import UploadValidationError, validate_text_file

    valid = tmp_path / ("valid" + extension)
    valid.write_bytes("非遗文本".encode("utf-8"))
    validate_text_file(valid)

    invalid = tmp_path / ("invalid" + extension)
    invalid.write_bytes(b"text\x00binary")
    with pytest.raises(UploadValidationError):
        validate_text_file(invalid)
