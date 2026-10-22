"""上传、公开目录共用的技艺 ID/名称映射。"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable


FALLBACK_CRAFTS = (
    {"id": "jingtailan", "name": "景泰蓝"},
    {"id": "suxiu", "name": "苏绣"},
    {"id": "longquan_ci", "name": "龙泉青瓷"},
    {"id": "yixing_zisha", "name": "宜兴紫砂"},
    {"id": "wuhu_tiehua", "name": "芜湖铁画"},
    {"id": "shujin", "name": "蜀锦"},
    {"id": "jianzhi", "name": "剪纸"},
    {"id": "jingdezhen_ciqi", "name": "景德镇瓷器"},
    {"id": "nanjing_yunjin", "name": "南京云锦"},
    {"id": "dongyang_mudiao", "name": "东阳木雕"},
    {"id": "miaozu_laran", "name": "苗族蜡染"},
    {"id": "muban_nianhua", "name": "木版年画"},
    {"id": "kesi", "name": "缂丝"},
    {"id": "zhubian", "name": "竹编"},
    {"id": "yudiao", "name": "玉雕"},
    {"id": "qiqi", "name": "漆器"},
    {"id": "tangsancai", "name": "唐三彩"},
    {"id": "junci", "name": "钧瓷"},
    {"id": "ruci", "name": "汝瓷"},
    {"id": "nirenzhang", "name": "泥人张"},
    {"id": "piyingxi", "name": "皮影戏"},
    {"id": "zhuangjin", "name": "壮锦"},
    {"id": "jingju", "name": "京剧"},
)


class CraftCatalogError(ValueError):
    """客户端提交的技艺标识无法由受控目录唯一解析。"""


@dataclass(frozen=True)
class _Craft:
    craft_id: str
    name: str


class CraftCatalog:
    def __init__(self, entries: Iterable[dict[str, Any]]):
        crafts = tuple(
            _Craft(str(entry["id"]).strip(), str(entry["name"]).strip())
            for entry in entries
        )
        self._crafts = crafts
        self._by_id = {craft.craft_id: craft for craft in crafts}
        self._by_name = {craft.name: craft for craft in crafts}
        if len(self._by_id) != len(crafts) or len(self._by_name) != len(crafts):
            raise CraftCatalogError("技艺目录包含重复 ID 或名称")

    @classmethod
    def from_projection(cls, projection: Any | None) -> "CraftCatalog":
        if projection is None:
            return cls(FALLBACK_CRAFTS)
        entries = [
            {"id": entry["slug"], "name": entry["name"]}
            for entry in projection.encyclopedia_entries()
        ]
        return cls(entries)

    def as_api_items(self) -> list[dict[str, str]]:
        return [
            {"id": craft.craft_id, "name": craft.name}
            for craft in self._crafts
        ]

    def resolve(
        self,
        *,
        craft_id: str | None = None,
        craft_name: str | None = None,
    ) -> tuple[str, str]:
        normalized_id = (craft_id or "").strip()
        normalized_name = (craft_name or "").strip()
        if not normalized_id and not normalized_name:
            raise CraftCatalogError("craft_id 或 craft_name 至少提供一个")

        by_id = self._by_id.get(normalized_id) if normalized_id else None
        by_name = self._by_name.get(normalized_name) if normalized_name else None
        if normalized_id and by_id is None:
            raise CraftCatalogError("未知 craft_id")
        if normalized_name and by_name is None:
            raise CraftCatalogError("未知 craft_name")
        if by_id is not None and by_name is not None and by_id != by_name:
            raise CraftCatalogError("craft_id 与 craft_name 不匹配")

        craft = by_id or by_name
        if craft is None:  # pragma: no cover - 上述分支已覆盖，仅保护类型收窄
            raise CraftCatalogError("无法解析技艺")
        return craft.craft_id, craft.name
