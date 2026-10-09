"""Public read models derived exclusively from the active local-books corpus."""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
from pathlib import Path
import re
from typing import Any

from src.graph.heritage_graph import HeritageKnowledgeGraph
from src.services.book_image_assets import IMAGE_SELECTION_VERSION


DEFAULT_CORPUS_PATH = Path(__file__).resolve().parents[2] / "data" / "local_books_corpus"
_NON_PROJECT_NAMES = frozenset({"申报地区或单位", "申报地区", "项目保护单位", "目录", "索引", "附录"})
_UNSAFE_DESCRIPTION_MARKERS = ("目录", "索引", "附录", "申报地区或单位", "项目保护单位")


class ActiveBooksProjectionError(RuntimeError):
    """The active corpus is missing or its public metadata is unsafe to use."""


@dataclass(frozen=True)
class ActiveBooksProjection:
    root: Path
    catalog: dict[str, Any]
    metadata: dict[str, Any]
    image_manifest: dict[str, Any]

    @classmethod
    def load(cls, root: Path | str = DEFAULT_CORPUS_PATH) -> "ActiveBooksProjection":
        root = Path(root)
        catalog = _read_json(root / "catalog.json", "catalog")
        if catalog.get("status") != "active" or not isinstance(catalog.get("corpus_id"), str):
            raise ActiveBooksProjectionError("本地图书语料未激活")
        metadata = _read_json(root / "craft_metadata.json", "技艺元数据")
        if metadata.get("corpus_id") != catalog["corpus_id"]:
            raise ActiveBooksProjectionError("技艺元数据与活动语料版本不一致")
        if not isinstance(metadata.get("projects"), list):
            raise ActiveBooksProjectionError("技艺元数据缺少 projects")
        image_manifest = {"images": {}}
        image_path = root / "book_images.json"
        if image_path.is_file():
            image_manifest = _read_json(image_path, "图书图片资产")
            if image_manifest.get("corpus_id") != catalog["corpus_id"]:
                raise ActiveBooksProjectionError("图书图片资产与活动语料版本不一致")
            if not isinstance(image_manifest.get("images"), dict):
                raise ActiveBooksProjectionError("图书图片资产缺少 images")
        return cls(root=root, catalog=catalog, metadata=metadata, image_manifest=image_manifest)

    @classmethod
    def try_load(cls, root: Path | str = DEFAULT_CORPUS_PATH) -> "ActiveBooksProjection | None":
        root = Path(root)
        catalog_path = root / "catalog.json"
        if not catalog_path.is_file():
            return None
        return cls.load(root)

    @property
    def projects(self) -> list[dict[str, Any]]:
        return [
            project for project in self.metadata["projects"]
            if project.get("project_name") not in _NON_PROJECT_NAMES
        ]

    def dashboard_summary(self) -> dict[str, int]:
        return {
            "source_books": int(self.catalog.get("source_count", 0)),
            "document_count": int(self.catalog.get("document_count", 0)),
            "total_characters": _total_characters(self.root / "documents.jsonl"),
            "project_count": len(self.projects),
            "inheritor_count": len(self.inheritors()),
        }

    def encyclopedia_entries(self) -> list[dict[str, Any]]:
        return [self._encyclopedia_entry(project, include_content=False) for project in self.projects]

    def encyclopedia_entry(self, slug: str) -> dict[str, Any] | None:
        for project in self.projects:
            if project.get("craft_id") == slug:
                return self._encyclopedia_entry(project, include_content=True)
        return None

    def inheritors(self) -> list[dict[str, Any]]:
        items = [item for project in self.projects for item in self._project_inheritors(project)]
        return sorted(items, key=lambda item: (item["name"], item["craft_name"]))

    def inheritor(self, slug: str) -> dict[str, Any] | None:
        return next((item for item in self.inheritors() if item["slug"] == slug), None)

    def build_graph(self) -> HeritageKnowledgeGraph:
        graph = HeritageKnowledgeGraph()
        for project in self.projects:
            craft_id = f"books:craft:{project['craft_id']}"
            graph.add_node(craft_id, "craft", project["project_name"], {
                "craft_id": project["craft_id"],
                "status": project.get("status", "mentioned"),
            })
            category = project.get("category", {}).get("value")
            if category:
                category_id = f"books:category:{sha256(category.encode('utf-8')).hexdigest()[:12]}"
                graph.add_node(category_id, "category", category, {})
                graph.add_edge(craft_id, category_id, "related_to", {})
            for region in project.get("regions", []):
                value = region.get("value")
                if not value:
                    continue
                region_id = f"books:region:{sha256(value.encode('utf-8')).hexdigest()[:12]}"
                graph.add_node(region_id, "region", value, {})
                graph.add_edge(craft_id, region_id, "originates_from", {})
            for inheritor in self._project_inheritors(project):
                name = inheritor.get("name")
                if not name:
                    continue
                inheritor_id = f"books:inheritor:{project['craft_id']}:{sha256(name.encode('utf-8')).hexdigest()[:12]}"
                graph.add_node(inheritor_id, "inheritor", name, {"recognition": inheritor.get("recognition", "")})
                graph.add_edge(inheritor_id, craft_id, "mastered_by", {})
            sources = project.get("sources", [])
            if sources:
                title = sources[0].get("book_title", "")
                if title:
                    source_id = f"books:source:{sha256(title.encode('utf-8')).hexdigest()[:12]}"
                    graph.add_node(source_id, "source", title, {})
                    graph.add_edge(craft_id, source_id, "has_source", {})
        graph._initialized = True
        return graph

    def _encyclopedia_entry(self, project: dict[str, Any], *, include_content: bool) -> dict[str, Any]:
        source_description = project.get("description", {})
        description = source_description.get("text", "")
        if len(source_description.get("evidence", [])) > 1 or any(marker in description for marker in _UNSAFE_DESCRIPTION_MARKERS):
            description = ""
        entry = {
            "name": project["project_name"],
            "slug": project["craft_id"],
            "summary": _list_summary(description) if description else "本条目来自当前活动图书知识库。",
            "image": self._image(project["craft_id"]),
        }
        if include_content:
            entry["content"] = description
        return entry

    def _image(self, craft_id: str) -> dict[str, str | None]:
        image = self.image_manifest["images"].get(craft_id)
        if (
            self.image_manifest.get("selection_version") != IMAGE_SELECTION_VERSION
            or not isinstance(image, dict)
            or image.get("status") != "extracted"
            or image.get("selection_version") != IMAGE_SELECTION_VERSION
        ):
            return {"url": None, "status": "unavailable"}
        # The browser reaches the backend through the same /api proxy as JSON endpoints.
        return {"url": f"/api/local-books/images/{craft_id}", "status": "extracted"}

    def image_file(self, craft_id: str) -> Path | None:
        image = self.image_manifest["images"].get(craft_id)
        if (
            self.image_manifest.get("selection_version") != IMAGE_SELECTION_VERSION
            or not isinstance(image, dict)
            or image.get("status") != "extracted"
            or image.get("selection_version") != IMAGE_SELECTION_VERSION
        ):
            return None
        file_path = image.get("file_path")
        if not isinstance(file_path, str):
            return None
        root = self.root.resolve()
        candidate = (root / file_path).resolve()
        if not candidate.is_file():
            return None
        try:
            candidate.relative_to(root)
        except ValueError:
            return None
        return candidate

    def _project_inheritors(self, project: dict[str, Any]) -> list[dict[str, Any]]:
        region = next((item.get("value", "") for item in project.get("regions", []) if item.get("value")), "")
        items = []
        for inheritor in project.get("inheritors", []):
            name = inheritor.get("name")
            if not name:
                continue
            evidence = [
                item for item in inheritor.get("evidence", [])
                if "国家级非物质文化遗产项目代表性传承人大典" in str(item.get("book_title", ""))
            ]
            if not evidence:
                continue
            items.append({
                "name": name,
                "slug": _inheritor_slug(project["craft_id"], name),
                "craft_name": project["project_name"],
                "region": region,
                "recognition": inheritor.get("recognition", ""),
                "biography": str(evidence[0].get("excerpt", "")),
                "lineage": "",
                "representative_works": "",
                "sources": [_public_source(item) for item in evidence],
            })
        return items


def _list_summary(description: str, limit: int = 180) -> str:
    """Keep long source text for the detail view while cards remain scannable."""
    normalized = re.sub(r"\s+", " ", description).strip()
    if len(normalized) <= limit:
        return normalized
    sentence_end = max(normalized.rfind(mark, 0, limit + 1) for mark in "。！？")
    if max(24, limit // 3) <= sentence_end < limit:
        return normalized[:sentence_end + 1]
    return normalized[:limit - 1].rstrip("，、；：") + "…"


def _read_json(path: Path, label: str) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ActiveBooksProjectionError(f"无法读取{label}：{error}") from error
    if not isinstance(data, dict):
        raise ActiveBooksProjectionError(f"{label}格式无效")
    return data


def _total_characters(path: Path) -> int:
    if not path.is_file():
        raise ActiveBooksProjectionError("活动语料缺少 documents.jsonl")
    total = 0
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            item = json.loads(line)
            total += int(item.get("char_count", len(item.get("content", ""))))
        except (ValueError, TypeError, json.JSONDecodeError) as error:
            raise ActiveBooksProjectionError(f"活动语料 documents.jsonl 无效：{error}") from error
    return total


def _inheritor_slug(craft_id: str, name: str) -> str:
    return f"{craft_id}-{sha256(name.encode('utf-8')).hexdigest()[:12]}"


def _public_source(evidence: dict[str, Any]) -> dict[str, str]:
    title = str(evidence.get("book_title", "未标注图书"))
    page = evidence.get("page")
    return {
        "name": f"{title} 第{page}页" if page else title,
        "url": "",
        "evidence": str(evidence.get("excerpt", "")),
    }
