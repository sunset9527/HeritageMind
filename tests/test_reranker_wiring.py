# -*- coding: utf-8 -*-
"""Reranker 接线测试（v2.2）：config 默认值 + retrieve 三路径 + 置顶保护

背景：reranker.py 原为死代码（类+单例已实现但检索链路从未调用，README 却声称已用）。
v2.2 接入 retriever.retrieve：置顶文档保护 + 候选池截断精排 + 模型不可用快速降级。
本机 bge-reranker-base 权重未下载完整 + 无外网 → reranker_enabled 默认 False。

运行：python -m pytest tests/test_reranker_wiring.py -v
"""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import logging
logging.basicConfig(level=logging.ERROR)

from config import settings
from src.retrieval.retriever import MultiSourceRetriever

Q_SEMANTIC = "哪个非遗项目的雕刻技法最擅长表现人物？"
Q_CRAFT = "景泰蓝的制作工艺中掐丝和点蓝分别是什么？"


def _new_retriever() -> MultiSourceRetriever:
    return MultiSourceRetriever()


class TestRerankerConfig:
    def test_reranker_disabled_by_default(self):
        """本机模型不可用（权重 0 字节 + 无外网）→ 默认关闭，避免每次检索卡网络超时"""
        assert settings.reranker_enabled is False


class TestRerankerWiring:
    def test_retrieve_disabled_fast_no_rerank_score(self):
        retriever = _new_retriever()
        t0 = time.time()
        results = retriever.retrieve(Q_SEMANTIC, top_k=5)
        dt = time.time() - t0
        assert len(results) > 0
        assert not any("rerank_score" in r for r in results), "关闭 rerank 不应有 rerank_score"
        assert dt < 10, f"关闭 rerank 应快速返回，实测 {dt:.1f}s"

    def test_retrieve_enabled_model_unavailable_degrades_fast(self, monkeypatch):
        """启用但模型不可用（模拟 _load 失败）→ 快速降级按原分数排序，不卡网络"""
        retriever = _new_retriever()
        old = settings.reranker_enabled
        settings.reranker_enabled = True
        try:
            import src.retrieval.reranker as reranker_mod

            class _UnavailableReranker:
                def rerank(self, query, documents, top_k=None):
                    return sorted(
                        documents,
                        key=lambda d: d.get("score", d.get("similarity", 0)),
                        reverse=True,
                    )[:top_k]

            monkeypatch.setattr(reranker_mod, "get_reranker_model", lambda: _UnavailableReranker())
            t0 = time.time()
            results = retriever.retrieve(Q_SEMANTIC, top_k=5)
            dt = time.time() - t0
            assert len(results) > 0
            assert not any("rerank_score" in r for r in results), "降级路径不应有 rerank_score"
            assert dt < 30, f"降级不应卡网络超时，实测 {dt:.1f}s"
        finally:
            settings.reranker_enabled = old

    def test_craft_boost_rank1_protected(self):
        """技艺名置顶文档保持 rank1（硬规则不被 rerank/排序冲掉）"""
        retriever = _new_retriever()
        results = retriever.retrieve(Q_CRAFT, top_k=5)
        assert results, "检索不应为空"
        top1 = results[0]
        assert top1.get("craft_name_boosted") or "jingtai" in str(top1.get("id", "")).lower(), \
            f"rank1 应为景泰蓝(置顶)，实际 {top1.get('id')}"
