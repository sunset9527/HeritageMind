"""
层级聚合模块（P2优化①）：技艺 → 工序 → 细节

背景：非遗知识在检索层常以"单条切片"形式返回（一条 chunk 只有技艺的某个
局部，如"掐丝是景泰蓝最关键的工序"），单条切片丢失全貌，生成阶段难以还原
完整技艺视图。本模块把检索命中的多条碎片按层级聚合成组：

    技艺（craft）  →  组：按 metadata.craft_id 归一化分组
    工序（process）→  组内排序：文档内容中的编号步骤/章节标题/文档顺序
    细节（detail） →  组内文档正文（拼接为完整技艺视图上下文）

层级字段假设（文档 metadata 无明确 section/order 字段时）：
1. 组归属用 craft_id（拼音 ID），兼容整篇文档与 chunk 碎片（id 去 _cN 后缀）
2. 组内顺序用"内容里检测到的第一个编号步骤序号"近似工序顺序；
   无编号步骤时回退到检索原始排名（保持召回顺序）
3. chunk 碎片场景下，同一技艺的 chunk 顺序（_c0/_c1/...）即文档顺序，
   与工序推进方向一致，可作为工序顺序的合理近似

输出结构：
    groups: {craft_id: {craft_name, docs, score, processes, coverage}}
    context: 按组拼接的"完整技艺视图"文本（可直接作为 LLM 上下文）
"""

import logging
import re
from typing import Dict, List, Any, Optional

from src.retrieval.document_loader import CRAFT_ID_TO_NAME, CRAFT_NAME_TO_ID
from src.retrieval.craft_name_boost import craft_id_of, find_matched_crafts

logger = logging.getLogger(__name__)

# 章节标题（## 开头）与编号步骤（1. / 1、）用于提取工序关键词
_SECTION_RE = re.compile(r"^#+\s*(.+)$")
_STEP_RE = re.compile(r"^\s*(\d+)\s*[\.、．]\s*(.+)$")
_CN_STEP_RE = re.compile(r"第([一二三四五六七八九十百]+)步")
# 常见的工序/流程提示词（文档中无编号时兜底识别）
_PROCESS_HINT_RE = re.compile(r"(工序|流程|步骤|工艺)")


def detect_process_keywords(content: str) -> List[str]:
    """
    从文档内容中提取工序关键词（编号步骤名 + 章节标题 + "第X步"）。

    Args:
        content: 文档正文

    Returns:
        工序关键词列表（按出现顺序去重）
    """
    if not content:
        return []
    keywords = []
    for line in content.split("\n"):
        line = line.strip()
        if not line:
            continue
        m = _STEP_RE.match(line)
        if m:
            step = m.group(2).strip().lstrip("*").strip()
            # 步骤名取"："或"。"前的短语，如 "1. **制胎**：用紫铜板…" → "制胎"
            step = re.split(r"[：:。]", step)[0].replace("*", "").strip()
            if step and step not in keywords:
                keywords.append(step)
            continue
        m = _SECTION_RE.match(line)
        if m:
            title = m.group(1).strip()
            if title and title not in keywords and len(title) <= 12:
                keywords.append(title)
            continue
        m = _CN_STEP_RE.search(line)
        if m and line not in keywords:
            keywords.append(line[:20])
    return keywords[:20]


def first_step_order(content: str) -> Optional[int]:
    """
    提取内容中第一个编号步骤的序号（用于组内工序排序）。

    Args:
        content: 文档正文

    Returns:
        第一个编号步骤的序号（1-based），无编号步骤时返回 None
    """
    if not content:
        return None
    for line in content.split("\n"):
        m = _STEP_RE.match(line.strip())
        if m:
            return int(m.group(1))
    return None


def doc_order_key(doc: Dict[str, Any], fallback: int) -> tuple:
    """
    组内排序键：优先 metadata 显式层级字段，其次内容工序序号，最后原始排名。

    Args:
        doc: 检索结果文档
        fallback: 回退排序值（通常传原始列表下标）

    Returns:
        (是否显式排序, 排序数值) —— 显式排序的排前面，再按数值升序
    """
    metadata = doc.get("metadata") or {}
    # 1. 显式层级字段（未来导入数据可写入 section_order / chunk_index）
    for field in ("section_order", "chunk_index", "seq"):
        v = metadata.get(field)
        if v is not None:
            try:
                return (1, float(v))
            except (TypeError, ValueError):
                pass
    # 2. 内容中的工序序号（编号步骤）
    order = first_step_order(doc.get("content", ""))
    if order is not None:
        return (1, float(order))
    # 3. 原始排名
    return (0, float(fallback))


def group_documents(
    results: List[Dict[str, Any]],
    query: Optional[str] = None,
) -> Dict[str, Dict[str, Any]]:
    """
    按"技艺 → 工序 → 细节"层级把检索结果聚合成组。

    Args:
        results: 检索结果列表（已排序）
        query: 可选查询文本（命中技艺名的组优先展示）

    Returns:
        groups: {craft_id: {craft_name, docs, score, processes, coverage}}
    """
    groups: Dict[str, Dict[str, Any]] = {}
    for idx, doc in enumerate(results):
        cid = craft_id_of(doc)
        if cid is None:
            # 无法归组的文档：放入虚拟组 "other"，保证信息不丢失
            cid = "other"
        if cid not in groups:
            groups[cid] = {
                "craft_id": cid,
                "craft_name": CRAFT_ID_TO_NAME.get(cid, cid),
                "docs": [],
                "score": 0.0,
                "processes": [],
            }
        group = groups[cid]
        group["docs"].append((idx, doc))
        group["score"] = max(group["score"], doc.get("score", doc.get("similarity", 0.0)))
        for kw in detect_process_keywords(doc.get("content", "")):
            if kw not in group["processes"]:
                group["processes"].append(kw)

    # 组内按工序顺序排序（技艺→工序→细节）
    for group in groups.values():
        group["docs"].sort(
            key=lambda item: doc_order_key(item[1], item[0])
        )
        group["docs"] = [doc for _, doc in group["docs"]]
        group["doc_count"] = len(group["docs"])

    # 组间排序：query 命中技艺名的组优先，其余按组内最高分降序
    matched = set(find_matched_crafts(query)) if query else set()
    matched_ids = {CRAFT_NAME_TO_ID.get(n, n): n for n in matched}
    groups_sorted = sorted(
        groups.values(),
        key=lambda g: (0 if g["craft_id"] in matched_ids else 1, -g["score"]),
    )
    return {g["craft_id"]: g for g in groups_sorted}


def build_grouped_context(
    groups: Dict[str, Dict[str, Any]],
    max_chars_per_group: int = 1500,
    include_processes: bool = True,
) -> str:
    """
    把分组结果拼接为"完整技艺视图"上下文文本。

    格式（每组）：
        【技艺：苏绣】（工序：勾样、上绷、配线、刺绣、落绷）
        <组内文档正文拼接>

    Args:
        groups: group_documents 的返回结果
        max_chars_per_group: 每组合并后最大字符数，超出截断（控制上下文体积）
        include_processes: 是否在组标题附加工序关键词

    Returns:
        拼接后的上下文文本
    """
    blocks = []
    for gid, group in groups.items():
        header = f"【技艺：{group['craft_name']}】"
        if include_processes and group.get("processes"):
            header += f"（工序：{'、'.join(group['processes'][:10])}）"
        parts = [header]
        total = len(header)
        for doc in group["docs"]:
            content = doc.get("content", "").strip()
            if not content:
                continue
            if total + len(content) > max_chars_per_group:
                remain = max_chars_per_group - total
                if remain > 20:
                    parts.append(content[:remain] + "…")
                    total += remain + 1
                break
            parts.append(content)
            total += len(content) + 1
        blocks.append("\n".join(parts))
    return "\n\n".join(blocks)


def group_retrieved_docs(
    results: List[Dict[str, Any]],
    query: Optional[str] = None,
    max_chars_per_group: int = 1500,
) -> Dict[str, Any]:
    """
    检索结果 → 层级聚合（纯函数，供 nodes / retriever.retrieve_grouped 复用）。

    Args:
        results: 检索结果列表
        query: 查询文本（用于组间优先排序）
        max_chars_per_group: 每组上下文字符上限

    Returns:
        {
            "groups": {craft_id: {...}},
            "context": 拼接上下文,
            "group_count": 组数,
            "total_docs": 参与聚合的文档数
        }
    """
    groups = group_documents(results, query)
    return {
        "groups": groups,
        "context": build_grouped_context(groups, max_chars_per_group=max_chars_per_group),
        "group_count": len(groups),
        "total_docs": len(results),
    }
