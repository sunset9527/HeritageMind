"""
技艺名精确匹配置顶模块（P2优化⑤）

背景：直问类问题（如"景泰蓝的制作工艺是怎样的？"）通常显式包含技艺名，
但混合检索（关键词 + 语义）可能因问题后半段的问法/术语把目标技艺文档挤下
rank1。本模块在检索结果后处理阶段做"精确匹配置顶"：

- 从 query 中精确匹配 23 种非遗技艺名（最长匹配优先，防止短名误匹配）
- 命中时，将该技艺的文档（含该技艺的所有 chunk 碎片）整体置顶到 rank1，
  其余结果保持原相对顺序
- 未命中技艺名时完全不干预排序（保证难题/推理题的零回归）

设计参考 LexRAG exact_article_boost（精确条号置顶）的同一思路：
规则简单、离线可复现、不依赖 LLM，且只影响"含技艺名"的 query。
"""

import logging
import re
from typing import Dict, List, Any, Optional, Tuple

from src.retrieval.document_loader import CRAFT_NAME_TO_ID, CRAFT_ID_TO_NAME

logger = logging.getLogger(__name__)

# 技艺名按长度降序排列：匹配时先尝试最长名称，避免短名命中长名场景
# 例：query 含"东阳木雕"时不能先命中"木雕"（"木雕"不在名单，但按长度降序更稳）
CRAFT_NAMES_SORTED: List[str] = sorted(
    CRAFT_NAME_TO_ID.keys(), key=lambda n: len(n), reverse=True
)

# chunk 文档 id 后缀约定（如 jingtailan_c0 / jingtailan_c1）
_CHUNK_SUFFIX_RE = re.compile(r"_c\d+$")


def find_matched_crafts(query: str) -> List[str]:
    """
    从 query 中精确匹配技艺名。

    Args:
        query: 用户查询文本

    Returns:
        命中的技艺中文名列表（按在 query 中首次出现的位置排序）
    """
    if not query:
        return []
    matched = []
    for name in CRAFT_NAMES_SORTED:
        # 已匹配过的名称跳过（防"剪纸"重复命中），同时避免同一位置重复
        if name in query and name not in matched:
            matched.append(name)
    # 按出现位置排序，保持 query 中的提及顺序
    matched.sort(key=lambda n: query.index(n))
    return matched


def is_craft_query(query: str) -> bool:
    """判断 query 是否包含任一已知技艺名（精确匹配）"""
    return len(find_matched_crafts(query)) > 0


def craft_id_of(doc: Dict[str, Any]) -> Optional[str]:
    """
    归一化任意检索结果文档所属的技艺 ID（craft_id）。

    兼容三种文档形态：
    1. 整篇文档：id == "jingtailan"，metadata.craft_id == "jingtailan"
    2. chunk 碎片：id == "jingtailan_c0"，metadata.craft_id == "jingtailan"
    3. 仅 metadata.craft_name（中文名）的文档：反查拼音 ID

    Args:
        doc: 检索结果文档（含 id / content / metadata）

    Returns:
        技艺 ID（拼音），无法识别时返回 None
    """
    metadata = doc.get("metadata") or {}
    doc_id = doc.get("id") or ""

    # 1. metadata.craft_id 最可靠
    craft_id = metadata.get("craft_id")
    if craft_id:
        return str(craft_id)

    # 2. metadata.craft_name 反查
    craft_name = metadata.get("craft_name")
    if craft_name and craft_name in CRAFT_NAME_TO_ID:
        return CRAFT_NAME_TO_ID[craft_name]

    # 3. 从 doc_id 推断：整篇 id 或 chunk id（去掉 _cN 后缀）
    if doc_id:
        base = _CHUNK_SUFFIX_RE.sub("", doc_id)
        if base in CRAFT_ID_TO_NAME:
            return base

    return None


def apply_craft_name_boost(
    results: List[Dict[str, Any]],
    query: str,
) -> Tuple[List[Dict[str, Any]], List[str]]:
    """
    技艺名精确匹配置顶（后处理）。

    规则：
    - query 命中技艺名 N 个，则把属于这 N 个技艺的文档从原列表中抽出，
      按"原列表相对顺序"整体放到最前（多技艺 query 时各技艺文档交错保持原序）
    - 每个被置顶的文档打上 craft_name_boosted=True 标记（可观测/可评测）
    - 未命中技艺名 → 原样返回，零改动
    - 目标技艺文档不在召回结果中 → 不伪造插入，仅提升已召回的

    Args:
        results: 检索结果列表（已按相似度排序）
        query: 用户查询文本

    Returns:
        (置顶后的结果列表, 命中的技艺名列表)
    """
    if not results:
        return results, []

    matched_names = find_matched_crafts(query)
    if not matched_names:
        return results, []

    matched_ids = {CRAFT_NAME_TO_ID[n] for n in matched_names}

    boosted, rest = [], []
    for doc in results:
        cid = craft_id_of(doc)
        if cid is not None and cid in matched_ids:
            doc["craft_name_boosted"] = True
            boosted.append(doc)
        else:
            rest.append(doc)

    if not boosted:
        # 目标技艺文档未被召回：不干预排序（检索诚实性优先）
        logger.debug(f"query 命中技艺名 {matched_names}，但结果中无对应文档，跳过置顶")
        return results, matched_names

    logger.info(f"技艺名精确匹配置顶: {matched_names}，置顶 {len(boosted)} 篇文档")
    return boosted + rest, matched_names
