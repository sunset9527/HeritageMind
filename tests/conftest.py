"""全量离线回归的共享测试隔离。"""

import pytest

from config import settings
from src.retrieval.reranker import reset_reranker_model


@pytest.fixture(autouse=True)
def isolate_reranker_from_offline_tests():
    """常规测试不加载本机 CrossEncoder，且不泄露单例或配置状态。"""
    original_enabled = settings.reranker_enabled
    settings.reranker_enabled = False
    reset_reranker_model()
    try:
        yield
    finally:
        settings.reranker_enabled = original_enabled
        reset_reranker_model()
