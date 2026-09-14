"""Regression tests for deterministic knowledge-gap fallback behavior."""

from src.knowledge.gap_detector import KnowledgeGapDetector


class BrokenLlm:
    def invoke(self, prompt):
        raise RuntimeError("model unavailable")


def test_gap_detector_rejects_low_similarity_results_when_llm_is_unavailable():
    detector = KnowledgeGapDetector(llm=BrokenLlm())
    documents = [{"content": "无关资料", "similarity": 0.05} for _ in range(5)]

    result = detector.detect("帮我预订机票", documents)

    assert result.coverage_level == "missing"
    assert result.can_answer is False


def test_gap_detector_accepts_high_similarity_results_when_llm_is_unavailable():
    detector = KnowledgeGapDetector(llm=BrokenLlm())
    documents = [{"content": "相关资料", "similarity": 0.8} for _ in range(3)]

    result = detector.detect("景泰蓝如何制作", documents)

    assert result.coverage_level == "sufficient"
    assert result.can_answer is True


def test_gap_detector_uses_relevance_threshold_in_fallback_not_document_threshold():
    detector = KnowledgeGapDetector(llm=BrokenLlm())
    documents = [{"content": "相关资料", "similarity": 0.3} for _ in range(3)]

    result = detector.detect("景泰蓝如何制作", documents)

    assert result.coverage_level == "partial"
    assert result.can_answer is True
