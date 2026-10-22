"""上传文件的有限读取、类型识别和路径边界。"""

from __future__ import annotations

import codecs
import hashlib
import os
import re
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import FrozenSet
from uuid import uuid4

from starlette.datastructures import UploadFile

from config import settings


class UploadValidationError(ValueError):
    def __init__(self, code: str, detail: str, status_code: int = 400):
        super().__init__(detail)
        self.code = code
        self.detail = detail
        self.status_code = status_code


@dataclass(frozen=True)
class DetectedFile:
    format: str
    extension: str
    mime_type: str


@dataclass(frozen=True)
class UploadPolicy:
    formats: FrozenSet[str]
    max_bytes: int
    chunk_bytes: int = 64 * 1024
    max_dimension: int = settings.image_max_dimension
    max_pixels: int = settings.image_max_pixels
    docx_max_members: int = 2_048
    docx_max_uncompressed_bytes: int = 50 * 1024 * 1024
    docx_max_ratio: float = 100.0


@dataclass(frozen=True)
class StagedUpload:
    temp_path: Path
    storage_name: str
    original_name: str
    format: str
    extension: str
    mime_type: str
    size_bytes: int
    content_sha256: str


_FORMAT_RULES = {
    "jpeg": {"extensions": {".jpg", ".jpeg"}, "mimes": {"image/jpeg"}, "extension": ".jpg"},
    "png": {"extensions": {".png"}, "mimes": {"image/png"}, "extension": ".png"},
    "webp": {"extensions": {".webp"}, "mimes": {"image/webp"}, "extension": ".webp"},
    "mp3": {"extensions": {".mp3"}, "mimes": {"audio/mpeg", "audio/mp3"}, "extension": ".mp3"},
    "wav": {"extensions": {".wav"}, "mimes": {"audio/wav", "audio/x-wav", "audio/wave"}, "extension": ".wav"},
    "m4a": {"extensions": {".m4a"}, "mimes": {"audio/mp4", "audio/x-m4a", "audio/m4a"}, "extension": ".m4a"},
    "flac": {"extensions": {".flac"}, "mimes": {"audio/flac", "audio/x-flac"}, "extension": ".flac"},
    "ogg": {"extensions": {".ogg", ".oga"}, "mimes": {"audio/ogg", "application/ogg"}, "extension": ".ogg"},
    "pdf": {"extensions": {".pdf"}, "mimes": {"application/pdf"}, "extension": ".pdf"},
    "docx": {
        "extensions": {".docx"},
        "mimes": {"application/vnd.openxmlformats-officedocument.wordprocessingml.document"},
        "extension": ".docx",
    },
    "md": {"extensions": {".md", ".markdown"}, "mimes": {"text/markdown", "text/x-markdown"}, "extension": ".md"},
    "txt": {"extensions": {".txt"}, "mimes": {"text/plain"}, "extension": ".txt"},
}
_EXTENSION_TO_FORMAT = {
    extension: format_name
    for format_name, rule in _FORMAT_RULES.items()
    for extension in rule["extensions"]
}
_CONTROL_CHARS = re.compile(r"[\x00-\x1f\x7f]")
_REQUIRED_DOCX_MEMBERS = {"[Content_Types].xml", "_rels/.rels", "word/document.xml"}


def validate_original_filename(filename: str | None) -> str:
    name = (filename or "").strip()
    if (
        not name
        or len(name) > 255
        or "/" in name
        or "\\" in name
        or _CONTROL_CHARS.search(name)
        or Path(name).is_absolute()
        or re.match(r"^[A-Za-z]:", name)
    ):
        raise UploadValidationError("invalid_filename", "文件名不合法")
    return name


def _declared_mime(mime_type: str | None) -> str:
    return (mime_type or "").split(";", 1)[0].strip().lower()


def _detect_binary_format(header: bytes) -> str | None:
    if header.startswith(b"\xff\xd8\xff"):
        return "jpeg"
    if header.startswith(b"\x89PNG\r\n\x1a\n"):
        return "png"
    if len(header) >= 12 and header.startswith(b"RIFF") and header[8:12] == b"WEBP":
        return "webp"
    if header.startswith(b"ID3") or (len(header) >= 2 and header[0] == 0xFF and header[1] & 0xE0 == 0xE0):
        return "mp3"
    if len(header) >= 12 and header.startswith(b"RIFF") and header[8:12] == b"WAVE":
        return "wav"
    if len(header) >= 12 and header[4:8] == b"ftyp" and any(
        brand in header[8:64] for brand in (b"M4A ", b"M4B ", b"isom", b"mp42")
    ):
        return "m4a"
    if header.startswith(b"fLaC"):
        return "flac"
    if header.startswith(b"OggS"):
        return "ogg"
    if header.startswith(b"%PDF-"):
        return "pdf"
    if header.startswith(b"PK\x03\x04"):
        return "docx"
    return None


def validate_file_identity(filename: str, mime_type: str | None, header: bytes) -> DetectedFile:
    safe_name = validate_original_filename(filename)
    extension = Path(safe_name).suffix.lower()
    expected_format = _EXTENSION_TO_FORMAT.get(extension)
    if expected_format is None:
        raise UploadValidationError("unsupported_file_type", "不支持的文件格式", 415)

    rule = _FORMAT_RULES[expected_format]
    declared_mime = _declared_mime(mime_type)
    if declared_mime not in rule["mimes"]:
        raise UploadValidationError("mime_mismatch", "文件扩展名与声明 MIME 不一致", 415)

    if expected_format in {"md", "txt"}:
        if b"\x00" in header:
            raise UploadValidationError("signature_mismatch", "文本文件包含二进制内容", 415)
        try:
            header.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise UploadValidationError("signature_mismatch", "文本文件不是 UTF-8", 415) from exc
        detected_format = expected_format
    else:
        detected_format = _detect_binary_format(header)
    if detected_format != expected_format:
        raise UploadValidationError("signature_mismatch", "文件扩展名、MIME 与文件签名不一致", 415)

    return DetectedFile(
        format=expected_format,
        extension=str(rule["extension"]),
        mime_type=declared_mime,
    )


def resolve_under(root: Path | str, name: str) -> Path:
    resolved_root = Path(root).resolve()
    candidate = (resolved_root / name).resolve()
    try:
        candidate.relative_to(resolved_root)
    except ValueError as exc:
        raise UploadValidationError("path_escape", "目标路径越界") from exc
    return candidate


async def stage_upload(upload: UploadFile, directory: Path | str, policy: UploadPolicy) -> StagedUpload:
    original_name = validate_original_filename(upload.filename)
    extension = Path(original_name).suffix.lower()
    format_from_extension = _EXTENSION_TO_FORMAT.get(extension)
    if format_from_extension is None:
        raise UploadValidationError("unsupported_file_type", "不支持的文件格式", 415)
    canonical_extension = str(_FORMAT_RULES[format_from_extension]["extension"])

    root = Path(directory)
    root.mkdir(parents=True, exist_ok=True)
    storage_name = f"{uuid4().hex}{canonical_extension}"
    temp_path = resolve_under(root, storage_name + ".part")
    digest = hashlib.sha256()
    total = 0
    header = bytearray()

    try:
        with temp_path.open("xb") as output:
            while True:
                chunk = await upload.read(policy.chunk_bytes)
                if not chunk:
                    break
                total += len(chunk)
                if total > policy.max_bytes:
                    raise UploadValidationError("file_too_large", "文件超过允许大小", 413)
                if len(header) < 4096:
                    header.extend(chunk[: 4096 - len(header)])
                digest.update(chunk)
                output.write(chunk)
        if total == 0:
            raise UploadValidationError("empty_file", "文件不能为空")

        detected = validate_file_identity(original_name, upload.content_type, bytes(header))
        if detected.format not in policy.formats:
            raise UploadValidationError("unsupported_file_type", "此入口不接受该文件格式", 415)
        if detected.format in {"jpeg", "png", "webp"}:
            validate_image_file(
                temp_path,
                max_dimension=policy.max_dimension,
                max_pixels=policy.max_pixels,
            )
        elif detected.format == "docx":
            validate_docx_archive(
                temp_path,
                max_members=policy.docx_max_members,
                max_uncompressed_bytes=policy.docx_max_uncompressed_bytes,
                max_ratio=policy.docx_max_ratio,
            )
        elif detected.format in {"md", "txt"}:
            validate_text_file(temp_path, max_bytes=policy.max_bytes)

        return StagedUpload(
            temp_path=temp_path,
            storage_name=storage_name,
            original_name=original_name,
            format=detected.format,
            extension=detected.extension,
            mime_type=detected.mime_type,
            size_bytes=total,
            content_sha256=digest.hexdigest(),
        )
    except Exception:
        try:
            temp_path.unlink(missing_ok=True)
        except OSError:
            pass
        raise


def validate_image_file(path: Path | str, *, max_dimension: int, max_pixels: int) -> None:
    try:
        from PIL import Image

        with Image.open(path) as image:
            width, height = image.size
            if width < 1 or height < 1 or width > max_dimension or height > max_dimension or width * height > max_pixels:
                raise UploadValidationError("image_dimensions_exceeded", "图片尺寸超过允许范围", 413)
            image.verify()
    except UploadValidationError:
        raise
    except Exception as exc:
        raise UploadValidationError("invalid_image", "图片无法解码", 415) from exc


def validate_docx_archive(
    path: Path | str,
    *,
    max_members: int,
    max_uncompressed_bytes: int,
    max_ratio: float,
) -> None:
    try:
        with zipfile.ZipFile(path) as archive:
            members = archive.infolist()
            names = {member.filename for member in members}
            if not _REQUIRED_DOCX_MEMBERS.issubset(names):
                raise UploadValidationError("invalid_docx", "DOCX 缺少必要结构", 415)
            if len(members) > max_members:
                raise UploadValidationError("archive_limits_exceeded", "DOCX 成员数量超限", 413)
            total_size = 0
            total_compressed = 0
            for member in members:
                normalized = member.filename.replace("\\", "/")
                if normalized.startswith("/") or ".." in Path(normalized).parts or member.flag_bits & 0x1:
                    raise UploadValidationError("invalid_docx", "DOCX 包含非法成员", 415)
                total_size += member.file_size
                total_compressed += member.compress_size
            ratio = total_size / max(total_compressed, 1)
            if total_size > max_uncompressed_bytes or ratio > max_ratio:
                raise UploadValidationError("archive_limits_exceeded", "DOCX 解压规模超限", 413)
    except UploadValidationError:
        raise
    except (OSError, zipfile.BadZipFile) as exc:
        raise UploadValidationError("invalid_docx", "DOCX 压缩包无效", 415) from exc


def validate_text_file(path: Path | str, *, max_bytes: int = 2 * 1024 * 1024) -> None:
    decoder = codecs.getincrementaldecoder("utf-8")("strict")
    total = 0
    try:
        with Path(path).open("rb") as source:
            while True:
                chunk = source.read(64 * 1024)
                if not chunk:
                    break
                total += len(chunk)
                if total > max_bytes:
                    raise UploadValidationError("file_too_large", "文本文件超过允许大小", 413)
                if b"\x00" in chunk:
                    raise UploadValidationError("invalid_text", "文本文件包含二进制内容", 415)
                decoder.decode(chunk)
            decoder.decode(b"", final=True)
    except UploadValidationError:
        raise
    except UnicodeDecodeError as exc:
        raise UploadValidationError("invalid_text", "文本文件不是 UTF-8", 415) from exc


def finalize_staged_upload(staged: StagedUpload, directory: Path | str) -> Path:
    final_path = resolve_under(directory, staged.storage_name)
    os.replace(staged.temp_path, final_path)
    return final_path
