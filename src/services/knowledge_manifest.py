"""Offline validation for curated knowledge-source packages."""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
from pathlib import Path
from typing import Any


VALID_STATUSES = frozenset({"draft", "published", "legacy_unverified", "deprecated"})
VALID_EVIDENCE_LAYERS = frozenset({"registry_record", "curated_summary", "deep_summary"})
REQUIRED_DOCUMENT_FIELDS = frozenset({
    "document_key",
    "craft_name",
    "title",
    "content_path",
    "source_name",
    "source_url",
    "accessed_at",
    "license_note",
    "status",
})


class ManifestValidationError(ValueError):
    """Raised when a knowledge-source package cannot be safely imported."""


@dataclass(frozen=True)
class ManifestDocument:
    document_key: str
    craft_name: str
    title: str
    content_path: Path
    content: str
    content_sha256: str
    source_name: str
    source_url: str
    accessed_at: str
    license_note: str
    status: str
    evidence_layer: str = "curated_summary"
    evidence_dimensions: tuple[str, ...] = ()
    registry_document_key: str | None = None


@dataclass(frozen=True)
class KnowledgeManifest:
    dataset_version: str
    documents: tuple[ManifestDocument, ...]


def load_manifest(manifest_path: str | Path) -> KnowledgeManifest:
    """Load a UTF-8 manifest and reject malformed or unsafe document entries."""
    path = Path(manifest_path).resolve()
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as error:
        raise ManifestValidationError(f"manifest not found: {path}") from error
    except json.JSONDecodeError as error:
        raise ManifestValidationError(f"manifest is not valid JSON: {error.msg}") from error

    if not isinstance(payload, dict):
        raise ManifestValidationError("manifest root must be an object")
    dataset_version = _required_text(payload, "dataset_version", "manifest")
    raw_documents = payload.get("documents")
    if not isinstance(raw_documents, list) or not raw_documents:
        raise ManifestValidationError("documents must be a non-empty list")

    package_root = path.parent.resolve()
    documents = tuple(_parse_document(raw, package_root) for raw in raw_documents)
    _validate_unique_documents(documents)
    _validate_evidence_links(documents)
    return KnowledgeManifest(dataset_version=dataset_version, documents=documents)


def _parse_document(raw: Any, package_root: Path) -> ManifestDocument:
    if not isinstance(raw, dict):
        raise ManifestValidationError("document must be an object")
    document_key = _required_text(raw, "document_key", "document")
    missing = REQUIRED_DOCUMENT_FIELDS.difference(raw)
    if missing:
        raise ManifestValidationError(f"{document_key}: missing required fields: {', '.join(sorted(missing))}")

    values = {field: _required_text(raw, field, document_key) for field in REQUIRED_DOCUMENT_FIELDS}
    if not values["source_url"].startswith(("https://", "http://")):
        raise ManifestValidationError(f"{document_key}: source_url must be an http(s) URL")
    if values["status"] not in VALID_STATUSES:
        raise ManifestValidationError(f"{document_key}: status must be one of {', '.join(sorted(VALID_STATUSES))}")

    evidence_layer = raw.get("evidence_layer")
    if evidence_layer is None:
        evidence_layer = "registry_record" if document_key.startswith("mct-first-batch-") else "curated_summary"
    if not isinstance(evidence_layer, str) or evidence_layer not in VALID_EVIDENCE_LAYERS:
        raise ManifestValidationError(
            f"{document_key}: evidence_layer must be one of {', '.join(sorted(VALID_EVIDENCE_LAYERS))}"
        )
    evidence_dimensions = _evidence_dimensions(raw.get("evidence_dimensions"), document_key)
    registry_document_key = raw.get("registry_document_key")
    if registry_document_key is not None and (
        not isinstance(registry_document_key, str) or not registry_document_key.strip()
    ):
        raise ManifestValidationError(f"{document_key}: registry_document_key must be a non-empty string")
    registry_document_key = registry_document_key.strip() if registry_document_key else None
    if evidence_layer == "deep_summary":
        if not evidence_dimensions:
            raise ManifestValidationError(f"{document_key}: deep_summary requires evidence_dimensions")
        if registry_document_key is None:
            raise ManifestValidationError(f"{document_key}: deep_summary requires registry_document_key")

    content_path = _safe_content_path(package_root, values["content_path"], document_key)
    try:
        content = content_path.read_text(encoding="utf-8").strip()
    except FileNotFoundError as error:
        raise ManifestValidationError(f"{document_key}: content_path does not exist") from error
    if not content:
        raise ManifestValidationError(f"{document_key}: content must not be empty")

    return ManifestDocument(
        document_key=values["document_key"],
        craft_name=values["craft_name"],
        title=values["title"],
        content_path=content_path,
        content=content,
        content_sha256=sha256(content.encode("utf-8")).hexdigest(),
        source_name=values["source_name"],
        source_url=values["source_url"],
        accessed_at=values["accessed_at"],
        license_note=values["license_note"],
        status=values["status"],
        evidence_layer=evidence_layer,
        evidence_dimensions=evidence_dimensions,
        registry_document_key=registry_document_key,
    )


def _required_text(raw: dict[str, Any], field: str, context: str) -> str:
    value = raw.get(field)
    if not isinstance(value, str) or not value.strip():
        raise ManifestValidationError(f"{context}: {field} is required")
    return value.strip()


def _evidence_dimensions(value: Any, document_key: str) -> tuple[str, ...]:
    if value is None:
        return ()
    if not isinstance(value, list) or not value:
        raise ManifestValidationError(f"{document_key}: evidence_dimensions must be a non-empty list")
    dimensions = tuple(item.strip() for item in value if isinstance(item, str) and item.strip())
    if len(dimensions) != len(value) or len(set(dimensions)) != len(dimensions):
        raise ManifestValidationError(f"{document_key}: evidence_dimensions must contain unique non-empty strings")
    return dimensions


def _safe_content_path(package_root: Path, value: str, document_key: str) -> Path:
    candidate = (package_root / value).resolve()
    if candidate == package_root or package_root not in candidate.parents:
        raise ManifestValidationError(f"{document_key}: content_path must stay inside the package")
    return candidate


def _validate_unique_documents(documents: tuple[ManifestDocument, ...]) -> None:
    keys: set[str] = set()
    hashes: set[str] = set()
    for document in documents:
        if document.document_key in keys:
            raise ManifestValidationError(f"duplicate document_key: {document.document_key}")
        if document.content_sha256 in hashes:
            raise ManifestValidationError(f"duplicate content hash: {document.document_key}")
        keys.add(document.document_key)
        hashes.add(document.content_sha256)


def _validate_evidence_links(documents: tuple[ManifestDocument, ...]) -> None:
    documents_by_key = {document.document_key: document for document in documents}
    for document in documents:
        if document.evidence_layer != "deep_summary":
            continue
        registry = documents_by_key.get(document.registry_document_key or "")
        if registry is None or registry.evidence_layer != "registry_record":
            raise ManifestValidationError(
                f"{document.document_key}: registry_document_key must reference a registry_record"
            )
        if registry.craft_name != document.craft_name:
            raise ManifestValidationError(
                f"{document.document_key}: registry_document_key craft_name does not match deep source craft_name"
            )
