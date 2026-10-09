"""Extract source-backed encyclopedia images from active local-book PDFs."""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import io
import json
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any, Mapping


IMAGE_SELECTION_VERSION = 3


class BookImageAssetError(RuntimeError):
    """The active corpus cannot safely produce its image assets."""


@dataclass
class BookImageAssetBuilder:
    corpus_path: Path | str
    source_files: Mapping[str, Path | str]

    def __post_init__(self) -> None:
        self.corpus_path = Path(self.corpus_path)
        self.source_files = {key: Path(value) for key, value in self.source_files.items()}

    def build(self) -> dict[str, Any]:
        catalog = _read_json(self.corpus_path / "catalog.json")
        metadata = _read_json(self.corpus_path / "craft_metadata.json")
        if catalog.get("status") != "active" or metadata.get("corpus_id") != catalog.get("corpus_id"):
            raise BookImageAssetError("活动图书语料与项目元数据不一致")

        source_by_title = {source.get("book_title"): source for source in catalog.get("sources", [])}
        page_texts = _load_page_texts(self.corpus_path / "documents.jsonl")
        images_dir = self.corpus_path / "images"
        images_dir.mkdir(parents=True, exist_ok=True)
        manifest_path = self.corpus_path / "book_images.json"
        manifest = {"corpus_id": catalog["corpus_id"], "selection_version": IMAGE_SELECTION_VERSION, "images": {}}
        if manifest_path.is_file():
            manifest = _read_json(manifest_path)
            if manifest.get("corpus_id") != catalog["corpus_id"] or not isinstance(manifest.get("images"), dict):
                raise BookImageAssetError("已有图书图片资产与活动语料版本不一致")
            if manifest.get("selection_version") != IMAGE_SELECTION_VERSION:
                manifest = {"corpus_id": catalog["corpus_id"], "selection_version": IMAGE_SELECTION_VERSION, "images": {}}
        for project in metadata.get("projects", []):
            craft_id = project.get("craft_id")
            if not craft_id:
                continue
            if _completed_asset_exists(self.corpus_path, manifest["images"].get(craft_id)):
                continue
            image = self._build_project_image(
                craft_id,
                project.get("project_name", ""),
                project.get("sources", []),
                source_by_title,
                page_texts,
                images_dir,
            )
            manifest["images"][craft_id] = image
            _write_json(manifest_path, manifest)
        return manifest

    def _build_project_image(
        self,
        craft_id: str,
        project_name: str,
        evidence: list[dict[str, Any]],
        source_by_title: dict[str, dict[str, Any]],
        page_texts: dict[tuple[str, int], str],
        images_dir: Path,
    ) -> dict[str, Any]:
        ordered_evidence = sorted(
            evidence,
            key=lambda item: _evidence_score(project_name, item, page_texts),
            reverse=True,
        )
        for source_evidence in ordered_evidence:
            source = source_by_title.get(source_evidence.get("book_title"))
            if not source or source.get("format") != "pdf":
                continue
            source_path = self.source_files.get(source.get("sha256", ""))
            page = source_evidence.get("page")
            if source_path is None or not source_path.is_file() or not isinstance(page, int) or page < 1:
                continue
            if _is_contents_page(page_texts.get((source["book_title"], page), "")):
                continue
            extracted = _extract_largest_page_image(source_path, page)
            if extracted is None:
                extracted = _render_source_page_preview(source_path, page)
            if extracted is None:
                continue
            image_bytes, method = extracted
            output_path = images_dir / f"{craft_id}.png"
            _write_png(output_path, image_bytes)
            return {
                "status": "extracted",
                "book_title": source["book_title"],
                "page": page,
                "method": method,
                "selection_version": IMAGE_SELECTION_VERSION,
                "file_path": output_path.relative_to(self.corpus_path).as_posix(),
            }
        return {"status": "unavailable", "file_path": None}


def resolve_source_files(library_path: Path | str, catalog: Mapping[str, Any]) -> dict[str, Path]:
    """Match only catalogued books by checksum, independent of their display names."""
    expected = {source.get("sha256") for source in catalog.get("sources", []) if source.get("sha256")}
    matches: dict[str, Path] = {}
    for path in Path(library_path).iterdir():
        if not path.is_file() or path.suffix.lower() not in {".pdf", ".epub"}:
            continue
        digest = _sha256_file(path)
        if digest in expected:
            matches[digest] = path
    return matches


def _extract_largest_page_image(source_path: Path, page_number: int) -> tuple[bytes, str] | None:
    import fitz

    with fitz.open(source_path) as document:
        if page_number > len(document):
            return None
        page = document[page_number - 1]
        candidates = []
        for image in page.get_images(full=True):
            extracted = document.extract_image(image[0])
            if extracted.get("width", 0) >= 64 and extracted.get("height", 0) >= 64:
                candidates.append(extracted)
    if not candidates:
        return None
    image_bytes = max(candidates, key=lambda item: item["width"] * item["height"])["image"]
    cropped = _crop_scanned_page(image_bytes)
    return cropped if cropped is not None else (image_bytes, "embedded")


def _render_source_page_preview(source_path: Path, page_number: int) -> tuple[bytes, str] | None:
    """Use the cited book page itself when it has no separable illustration."""
    import fitz

    with fitz.open(source_path) as document:
        if page_number > len(document):
            return None
        pixmap = document[page_number - 1].get_pixmap(alpha=False)
    return pixmap.tobytes("png"), "page_preview"


def _write_png(path: Path, image_bytes: bytes) -> None:
    from PIL import Image

    with Image.open(io.BytesIO(image_bytes)) as image:
        image.convert("RGB").save(path, format="PNG")


def _crop_scanned_page(image_bytes: bytes) -> tuple[bytes, str] | None:
    """Crop the largest saturated visual block from a portrait whole-page scan."""
    import cv2
    import numpy as np
    from PIL import Image

    with Image.open(io.BytesIO(image_bytes)) as image:
        rgb = image.convert("RGB")
        width, height = rgb.size
        if height < width * 1.15:
            return None
        pixels = np.asarray(rgb)
    hsv = cv2.cvtColor(pixels, cv2.COLOR_RGB2HSV)
    mask = cv2.inRange(hsv, np.array([35, 45, 20]), np.array([179, 255, 245]))
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, np.ones((11, 11), dtype=np.uint8))
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        return None
    x, y, crop_width, crop_height = cv2.boundingRect(max(contours, key=cv2.contourArea))
    crop_area = crop_width * crop_height
    page_area = width * height
    if crop_area < page_area * 0.025 or crop_area > page_area * 0.75:
        return None
    padding = max(8, min(width, height) // 80)
    left, top = max(0, x - padding), max(0, y - padding)
    right, bottom = min(width, x + crop_width + padding), min(height, y + crop_height + padding)
    output = io.BytesIO()
    Image.fromarray(pixels[top:bottom, left:right]).save(output, format="PNG")
    return output.getvalue(), "scan_crop"


def _read_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise BookImageAssetError(f"无法读取 {path.name}: {error}") from error
    if not isinstance(payload, dict):
        raise BookImageAssetError(f"{path.name} 格式无效")
    return payload


def _sha256_file(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _completed_asset_exists(corpus_path: Path, asset: Any) -> bool:
    if (
        not isinstance(asset, dict)
        or asset.get("status") != "extracted"
        or asset.get("selection_version") != IMAGE_SELECTION_VERSION
    ):
        return False
    file_path = asset.get("file_path")
    if not isinstance(file_path, str):
        return False
    root = corpus_path.resolve()
    candidate = (root / file_path).resolve()
    try:
        candidate.relative_to(root)
    except ValueError:
        return False
    return candidate.is_file()


def _load_page_texts(path: Path) -> dict[tuple[str, int], str]:
    if not path.is_file():
        return {}
    pages: dict[tuple[str, int], list[str]] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        item = json.loads(line)
        metadata = item.get("metadata", {})
        title = metadata.get("book_title")
        page = metadata.get("page_start")
        if isinstance(title, str) and isinstance(page, int):
            pages.setdefault((title, page), []).append(str(item.get("content", "")))
    return {key: "\n".join(value) for key, value in pages.items()}


def _evidence_score(project_name: str, evidence: Mapping[str, Any], page_texts: Mapping[tuple[str, int], str]) -> int:
    title = evidence.get("book_title")
    page = evidence.get("page")
    if not isinstance(title, str) or not isinstance(page, int):
        return -1
    page_text = page_texts.get((title, page), "")
    if _is_contents_page(page_text):
        return -10_000
    return page_text.count(project_name) * 100 + min(len(page_text), 5_000) // 100


def _is_contents_page(page_text: str) -> bool:
    return "目录" in page_text[:160]


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False, newline="\n") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
        temporary = Path(handle.name)
    temporary.replace(path)
