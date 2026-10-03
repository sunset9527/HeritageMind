"""Build traceable registry records from the Ministry of Culture and Tourism's public list.

The generated records deliberately contain only catalogue facts (batch, number,
name, category and declaring locality).  They are a breadth layer for discovery,
not substitutes for project-level research summaries.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from html.parser import HTMLParser
import json
from pathlib import Path
import re
from urllib.request import Request, urlopen


SOURCE_URL = "https://zwgk.mct.gov.cn/zfxxgkml/fwzwhyc/202012/t20201206_916788.html"
SOURCE_NAME = "中华人民共和国文化和旅游部（国务院公布）"
EXPECTED_RECORDS = 518
ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = ROOT / "data" / "knowledge_sources" / "manifest.json"
DOCUMENT_DIRECTORY = MANIFEST_PATH.parent / "documents" / "registry"
RECORD_PREFIX = "mct-first-batch-"


class _PlainText(HTMLParser):
    """Turn the government page into lines while excluding page chrome."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._pieces: list[str] = []
        self._ignored_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in {"script", "style"}:
            self._ignored_depth += 1
        elif not self._ignored_depth and tag in {"br", "p", "div", "li", "tr"}:
            self._pieces.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag in {"script", "style"} and self._ignored_depth:
            self._ignored_depth -= 1
        elif not self._ignored_depth and tag in {"p", "div", "li", "tr"}:
            self._pieces.append("\n")

    def handle_data(self, data: str) -> None:
        if not self._ignored_depth:
            self._pieces.append(data)

    @property
    def text(self) -> str:
        return "".join(self._pieces)


@dataclass
class RegistryRecord:
    ordinal: int
    registry_code: str
    craft_name: str
    category: str
    declaring_locality: str


_CATEGORY = re.compile(r"^[一二三四五六七八九十]+、(?P<name>.+?)（共计\d+项）$")
_ROW = re.compile(
    r"^(?P<ordinal>\d{1,3})\s*(?P<code>[ⅠⅡⅢⅣⅤⅥⅦⅧⅨⅩ]+[—-]\d+)\s*(?P<tail>.+)$"
)
_LOCALITY_PREFIX = re.compile(
    r"北京市|天津市|上海市|重庆市|河北省|山西省|辽宁省|吉林省|黑龙江省|江苏省|浙江省|安徽省|"
    r"福建省|江西省|山东省|河南省|湖北省|湖南省|广东省|海南省|四川省|贵州省|云南省|陕西省|"
    r"甘肃省|青海省|台湾省|内蒙古自治区|广西壮族自治区|西藏自治区|宁夏回族自治区|新疆维吾尔自治区"
)


def _split_name_and_locality(tail: str) -> tuple[str, str]:
    parts = re.split(r"\s{2,}", tail.strip(), maxsplit=1)
    if len(parts) != 2:
        # Item 320 in the Ministry's public HTML omits the column padding
        # ("蜀绣四川省成都市").  Only split this documented layout defect at an
        # explicit provincial/municipal prefix; never infer a locality otherwise.
        locality_match = _LOCALITY_PREFIX.search(tail)
        if locality_match and locality_match.start() > 0:
            return tail[:locality_match.start()].strip(), tail[locality_match.start():].strip()
        raise ValueError(f"could not separate project name from declaring locality: {tail!r}")
    return parts[0].strip(), parts[1].strip()


def parse_registry_records(html: str) -> list[RegistryRecord]:
    parser = _PlainText()
    parser.feed(html)

    category = ""
    records: list[RegistryRecord] = []
    current: RegistryRecord | None = None
    locality_lines: list[str] = []

    def flush() -> None:
        nonlocal current, locality_lines
        if current is not None:
            current.declaring_locality = " ".join(locality_lines).strip()
            records.append(current)
        current = None
        locality_lines = []

    for raw_line in parser.text.splitlines():
        line = raw_line.replace("\xa0", " ").strip()
        if not line:
            continue
        category_match = _CATEGORY.match(line)
        if category_match:
            flush()
            category = category_match.group("name").strip()
            continue
        row_match = _ROW.match(line)
        if row_match:
            flush()
            ordinal = int(row_match.group("ordinal"))
            if not category or ordinal > EXPECTED_RECORDS:
                continue
            try:
                craft_name, locality = _split_name_and_locality(row_match.group("tail"))
            except ValueError as error:
                raise ValueError(f"record {ordinal} could not be parsed: {error}") from error
            current = RegistryRecord(
                ordinal=ordinal,
                registry_code=row_match.group("code"),
                craft_name=craft_name,
                category=category,
                declaring_locality=locality,
            )
            locality_lines = [locality]
            if ordinal == EXPECTED_RECORDS:
                flush()
                break
            continue
        if current is not None and len(records) < EXPECTED_RECORDS:
            locality_lines.append(line)

    flush()
    if len(records) != EXPECTED_RECORDS:
        raise ValueError(f"expected {EXPECTED_RECORDS} first-batch records, parsed {len(records)}")
    if [record.ordinal for record in records] != list(range(1, EXPECTED_RECORDS + 1)):
        raise ValueError("first-batch record ordinals are not a complete sequence from 1 to 518")
    return records


def _record_content(record: RegistryRecord) -> str:
    return "\n".join(
        [
            f"# {record.craft_name}",
            "",
            "## 来源化名录记录",
            f"- 国家级名录批次：第一批（2006 年公布）",
            f"- 序号：{record.ordinal}",
            f"- 名录编号：{record.registry_code}",
            f"- 门类：{record.category}",
            f"- 申报地区或单位：{record.declaring_locality}",
            "",
            "## 可引用摘要",
            (
                f"文化和旅游部公开的第一批国家级非物质文化遗产名录将“{record.craft_name}”"
                f"列为{record.category}门类，名录编号为 {record.registry_code}，"
                f"申报地区或单位为{record.declaring_locality}。"
            ),
            "",
            "## 使用边界",
            "本条为官方名录记录，仅支持名录归属、编号、门类与申报地区/单位的核验；不替代工艺、历史或传承的深度研究。",
            "",
        ]
    )


def _manifest_entry(record: RegistryRecord, accessed_at: str) -> dict[str, str]:
    key = f"{RECORD_PREFIX}{record.ordinal:03d}"
    return {
        "document_key": key,
        "craft_name": record.craft_name,
        "title": f"{record.craft_name}：第一批国家级非遗名录记录",
        "content_path": f"documents/registry/{key}.md",
        "source_name": SOURCE_NAME,
        "source_url": SOURCE_URL,
        "accessed_at": accessed_at,
        "license_note": "公开政府名录的事实性条目；本仓库仅保存可核验事实与来源链接，不转载通知说明原文。",
        "status": "published",
    }


def build_catalog(html: str, *, accessed_at: str | None = None) -> int:
    records = parse_registry_records(html)
    payload = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    prior_documents = [
        item for item in payload["documents"] if not item["document_key"].startswith(RECORD_PREFIX)
    ]
    accessed_at = accessed_at or date.today().isoformat()
    DOCUMENT_DIRECTORY.mkdir(parents=True, exist_ok=True)
    for record in records:
        key = f"{RECORD_PREFIX}{record.ordinal:03d}"
        (DOCUMENT_DIRECTORY / f"{key}.md").write_text(_record_content(record), encoding="utf-8")

    payload["dataset_version"] = "curated-v2-2026-10-03"
    payload["documents"] = prior_documents + [_manifest_entry(record, accessed_at) for record in records]
    MANIFEST_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return len(records)


def fetch_source() -> str:
    request = Request(SOURCE_URL, headers={"User-Agent": "HeritageMind-corpus-builder/1.0"})
    with urlopen(request, timeout=30) as response:  # noqa: S310 - fixed public-government URL
        return response.read().decode("utf-8")


def main() -> None:
    count = build_catalog(fetch_source())
    print(f"Wrote {count} official first-batch registry records to {MANIFEST_PATH}")


if __name__ == "__main__":
    main()
