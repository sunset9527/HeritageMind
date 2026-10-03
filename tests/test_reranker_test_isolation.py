"""常规离线回归不应加载真实 CrossEncoder。"""

from config import settings


def test_regular_tests_disable_reranker_by_default():
    """避免本机模型存在与否改变常规 pytest 的速度和结果。"""
    assert settings.reranker_enabled is False
