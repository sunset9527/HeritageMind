"""v1.4 转写文本切块纯函数测试。"""
from src.retrieval.audio_store import split_transcript


def test_empty_returns_empty():
    assert split_transcript("") == []
    assert split_transcript("   ") == []


def test_short_single_chunk():
    assert split_transcript("景泰蓝的工艺", max_chars=500) == ["景泰蓝的工艺"]


def test_no_punctuation_overlap_zero_reconstructs():
    text = "很" * 1200
    chunks = split_transcript(text, max_chars=500, overlap=0)
    assert len(chunks) > 1
    assert all(len(c) <= 500 for c in chunks)
    assert "".join(chunks) == text


def test_overlap_increases_chunk_count_but_keeps_coverage():
    """重叠覆盖让相邻块共享字符 → 块数多于无重叠，且不超限、全覆盖。"""
    text = "很" * 1200
    c_no = split_transcript(text, max_chars=200, overlap=0)
    c_ov = split_transcript(text, max_chars=200, overlap=50)
    assert len(c_ov) > len(c_no)  # overlap=50 的块推进步长 150 < 200 → 严格更多块
    assert all(len(c) <= 200 for c in c_ov)
    # 覆盖性：每个字符至少出现在某块
    joined = "".join(c_ov)
    assert all(ch in joined for ch in "很")


def test_sentence_boundary_cut():
    text = "第一句。" + "第二句" + "很" * 20 + "。"
    chunks = split_transcript(text, max_chars=10, overlap=0)
    assert chunks[0] == "第一句。"
    assert all(len(c) <= 10 for c in chunks)
    assert "".join(chunks) == text  # 首块在句号处断开，且拼接无丢失


def test_max_chars_one_guards():
    text = "abc"
    chunks = split_transcript(text, max_chars=1, overlap=0)
    assert "".join(chunks) == "abc"
