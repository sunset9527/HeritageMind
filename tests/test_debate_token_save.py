"""
P1优化验证测试：多专家辩论引擎上下文瘦身 + 检索复用 + 热门问答缓存

本测试不调用真实LLM，全部使用 mock 对象：
- FakeLLM：固定返回长文本，记录每次调用的 prompt
- FakeRetriever：固定返回文档，计数检索调用次数
- FakeAgent：llm=None，走 DebateEngine 自己的 self.llm（FakeLLM）

运行方式：
    python -m pytest tests/test_debate_token_save.py -v
    或
    python tests/test_debate_token_save.py
"""

import os
import sys
import time
from types import SimpleNamespace

# 确保项目根目录在 sys.path 中（直接运行脚本时生效）
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import settings
from src.agents.debate_engine import DebateEngine

# 模拟回答长度：4字符 * 300 = 1200字符，超过 debate_history_chars=800，可触发历史截断
FAKE_ANSWER = "测试回答" * 300
FAKE_ANSWER_LEN = len(FAKE_ANSWER)  # 1200


class FakeLLM:
    """模拟LLM：返回固定文本，记录调用次数与每次的prompt"""

    def __init__(self):
        self.call_count = 0
        self.prompts = []

    def invoke(self, prompt):
        self.call_count += 1
        self.prompts.append(prompt)
        return SimpleNamespace(content=FAKE_ANSWER)


class FakeRetriever:
    """模拟检索器：返回固定文档，计数 retrieve 调用次数"""

    def __init__(self):
        self.call_count = 0

    def retrieve(self, question, top_k=5):
        self.call_count += 1
        return [{"content": "测试文档内容" * 50} for _ in range(top_k)]


class FakeAgent:
    """模拟Agent：无llm，debate_engine._call_agent 会降级用 self.llm（FakeLLM）"""

    llm = None

    def __init__(self):
        self.call_count = 0


def _make_engine():
    """构造 DebateEngine 并注入 FakeLLM / FakeRetriever / FakeAgent"""
    llm = FakeLLM()
    retriever = FakeRetriever()
    agents = {name: FakeAgent() for name in ["craft_expert", "history_expert", "heritage_expert"]}
    engine = DebateEngine(agents=agents, llm=llm)
    engine.retriever = retriever  # 覆盖真实检索器
    return engine, llm, retriever


def _history_segment_lengths(prompt):
    """提取 prompt 中每个【专家 - 角色】历史段落的正文长度列表"""
    lengths = []
    lines = prompt.split("\n")
    i = 0
    while i < len(lines):
        if lines[i].startswith("【"):
            content_chars = 0
            i += 1
            while i < len(lines) and not lines[i].startswith("【") and not lines[i].startswith("##"):
                content_chars += len(lines[i])
                i += 1
            lengths.append(content_chars)
            continue
        i += 1
    return lengths


# ---------------------------------------------------------------------------
# 1. 辩论总开关（降级）
# ---------------------------------------------------------------------------

def test_should_debate_respects_debate_enabled():
    """debate_enabled=False 时 should_debate 直接返回 (False, '')，不触发辩论"""
    engine, _, _ = _make_engine()
    analysis = {"required_experts": ["craft_expert", "history_expert"], "complexity": "complex"}

    old = settings.debate_enabled
    try:
        settings.debate_enabled = False
        ok, mode = engine.should_debate("景泰蓝为什么能成为国宝级非遗？", analysis)
        assert ok is False
        assert mode == ""
    finally:
        settings.debate_enabled = old

    # 开启后恢复正常判定
    ok, mode = engine.should_debate("景泰蓝为什么能成为国宝级非遗？", analysis)
    assert ok is True
    assert mode == "progressive"


# ---------------------------------------------------------------------------
# 2. 递进辩论：轮次上限 + 检索复用 + 历史截断
# ---------------------------------------------------------------------------

def test_progressive_rounds_and_retrieval_reuse_and_truncation():
    engine, llm, retriever = _make_engine()

    session = engine.run_full_debate(
        question="景泰蓝为什么能成为国宝级非遗？",
        mode="progressive",
        context={}
    )

    # ① 轮次数 ≤ settings.debate_max_rounds（设计3轮，默认max=3）
    n_rounds = len(session.rounds)
    print(f"\n[progressive] 实际轮次数: {n_rounds} (上限 {settings.debate_max_rounds})")
    assert n_rounds <= settings.debate_max_rounds
    assert n_rounds == 3, "progressive 设计为3轮（原4轮去掉Round4回应）"

    # ② 检索复用：整个 run_full_debate 只检索一次
    print(f"[progressive] retriever.retrieve 调用次数: {retriever.call_count}")
    assert retriever.call_count == 1, "检索复用失败：应只检索一次"

    # ③ 历史截断：Round3 的 prompt 中历史段落应被截断到 800 字符并带省略号
    round3_prompt = llm.prompts[2]
    seg_lens = _history_segment_lengths(round3_prompt)
    print(f"[progressive] Round3 prompt 历史段落长度: {seg_lens} (原始每段 {FAKE_ANSWER_LEN})")
    assert "…" in round3_prompt, "历史截断未生效：prompt 中应出现省略号"
    for seg_len in seg_lens:
        assert seg_len <= settings.debate_history_chars + 1, "历史段落超过截断上限"

    # ④ 回答字数限制指令已注入
    assert f"5. 回答控制在 {settings.expert_answer_max_chars} 字以内" in round3_prompt

    # ⑤ 统计信息（用于报告）
    total_prompt_chars = sum(len(p) for p in llm.prompts)
    saved_by_truncation = sum(max(0, FAKE_ANSWER_LEN - seg_len) for seg_len in seg_lens)
    print(f"[progressive] LLM调用次数: {llm.call_count} (3轮发言 + 洞见提取 + 综合)")
    print(f"[progressive] 全部prompt总字符数: {total_prompt_chars}, 本轮历史截断节省: {saved_by_truncation} 字符")
    print(f"[progressive] Round3 prompt长度: {len(round3_prompt)} 字符（未截断估算: {len(round3_prompt) + saved_by_truncation}）")


# ---------------------------------------------------------------------------
# 3. 多视角辩论：5轮 → 3轮
# ---------------------------------------------------------------------------

def test_multi_perspective_rounds():
    engine, _, retriever = _make_engine()

    session = engine.run_full_debate(
        question="苏绣的传承面临哪些挑战？",
        mode="multi_perspective",
        context={}
    )

    n_rounds = len(session.rounds)
    roles = [r.role for r in session.rounds]
    print(f"\n[multi_perspective] 实际轮次数: {n_rounds} (原5轮，现保留3视角)")
    print(f"[multi_perspective] 各轮角色: {roles}")
    assert n_rounds == 3, "多视角辩论应保留3个专家视角"
    assert n_rounds <= settings.debate_max_rounds
    assert "质疑与反思" not in roles and "综合回应" not in roles
    print(f"[multi_perspective] retriever.retrieve 调用次数: {retriever.call_count}")
    assert retriever.call_count == 1


# ---------------------------------------------------------------------------
# 4. 并列辩论：去掉 heritage 回应，仅保留 craft 质疑
# ---------------------------------------------------------------------------

def test_parallel_rounds():
    engine, _, retriever = _make_engine()

    session = engine.run_full_debate(
        question="景泰蓝和苏绣有什么区别？",
        mode="parallel",
        context={}
    )

    n_rounds = len(session.rounds)
    roles = [r.role for r in session.rounds]
    print(f"\n[parallel] 实际发言次数: {n_rounds} (3并列发言 + 1 craft质疑，去掉heritage回应)")
    print(f"[parallel] 各轮角色: {roles}")
    assert n_rounds == 4, "并列辩论应保留3个并列发言 + 1个craft质疑"
    assert roles.count("并列发言") == 3
    assert roles.count("质疑") == 1
    assert "回应" not in roles
    print(f"[parallel] retriever.retrieve 调用次数: {retriever.call_count}")
    assert retriever.call_count == 1


# ---------------------------------------------------------------------------
# 5. debate_max_rounds 上限约束（max_rounds=2 时提前结束）
# ---------------------------------------------------------------------------

def test_debate_max_rounds_cap():
    engine, _, _ = _make_engine()
    old = settings.debate_max_rounds
    try:
        settings.debate_max_rounds = 2
        session = engine.run_full_debate(
            question="景泰蓝为什么能成为国宝级非遗？",
            mode="progressive",
            context={}
        )
        n_rounds = len(session.rounds)
        print(f"\n[max_rounds=2] progressive 实际轮次: {n_rounds}")
        assert n_rounds == 2, "max_rounds=2 时应提前结束在2轮"
    finally:
        settings.debate_max_rounds = old


# ---------------------------------------------------------------------------
# 6. 热门问答缓存：命中/归一化/TTL/LRU淘汰
# ---------------------------------------------------------------------------

def test_cache_hit_normalization_ttl():
    """v1.4：缓存语义迁至 src/services/cache.py（QaCache/MemoryCacheBackend），此处回归迁移等价。"""
    import asyncio

    import api  # noqa: F401  # 确认 api 层接线暴露 get_qa_cache
    from src.services.cache import MemoryCacheBackend, QaCache

    # api 层接线：/query 经 get_qa_cache() 门面读写
    assert api.get_qa_cache is not None
    assert isinstance(api.get_qa_cache(), QaCache)

    async def _scenario():
        b = MemoryCacheBackend()
        # 写入带空白的问题，用不同空白形式命中（归一化）
        await b.set(" 景泰蓝 为什么 ", "RESP_1")
        assert await b.get("景泰蓝为什么") == "RESP_1"
        print("\n[cache] 归一化命中 OK（' 景泰蓝 为什么 ' → '景泰蓝为什么'）")

        # TTL 过期：ttl_seconds=-1 → 写入后立即视为过期
        b2 = MemoryCacheBackend(ttl_seconds=-1)
        await b2.set("景泰蓝为什么", "RESP_1")
        assert await b2.get("景泰蓝为什么") is None
        print("[cache] TTL过期失效 OK")

    asyncio.run(_scenario())


def test_cache_lru_eviction():
    import asyncio

    from src.services.cache import MemoryCacheBackend

    async def _scenario():
        b = MemoryCacheBackend(max_entries=2)
        await b.set("a", "A")
        await b.set("b", "B")
        await b.set("c", "C")  # 超过上限，淘汰最旧的 a
        assert await b.get("a") is None
        assert await b.get("b") == "B"
        assert await b.get("c") == "C"

        # LRU刷新：访问 b 后再写入 d，应淘汰 c（b 刚被使用）
        await b.get("b")
        await b.set("d", "D")
        assert await b.get("c") is None
        assert await b.get("b") == "B"
        assert await b.get("d") == "D"
        print("[cache] LRU淘汰+命中刷新 OK（max_entries=2 场景）")

    asyncio.run(_scenario())


# ---------------------------------------------------------------------------
# 直接运行入口
# ---------------------------------------------------------------------------

def main():
    print("=" * 60)
    print("P1优化验证：辩论引擎上下文瘦身 + 缓存")
    print("=" * 60)
    test_should_debate_respects_debate_enabled()
    test_progressive_rounds_and_retrieval_reuse_and_truncation()
    test_multi_perspective_rounds()
    test_parallel_rounds()
    test_debate_max_rounds_cap()
    test_cache_hit_normalization_ttl()
    test_cache_lru_eviction()
    print("\n" + "=" * 60)
    print("全部测试通过 ✅")
    print("=" * 60)


if __name__ == "__main__":
    main()
