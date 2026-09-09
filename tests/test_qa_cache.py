"""v1.4 热门问答缓存测试（离线：Memory 后端用注入 FakeTime；Redis 后端用注入桩客户端）。"""
import pytest
from pydantic import BaseModel

from src.services import cache as cache_mod
from src.services.cache import (
    MemoryCacheBackend,
    QaCache,
    RedisCacheBackend,
    qa_cache_key,
)
from tests.redis_stub import StubRedis


class _Resp(BaseModel):
    """模拟 QueryResponse 的 pydantic v2 对象，验证 Redis 端 JSON 序列化路径。"""

    answer: str
    ts: int


# --------------------------------------------------------------------------- #
# key 归一化
# --------------------------------------------------------------------------- #
def test_normalize_strips_whitespace_and_lowercases():
    assert cache_mod._normalize_question("  景泰蓝  工艺  ") == "景泰蓝工艺"
    assert cache_mod._normalize_question("Cloisonné") == "cloisonné"


def test_qa_cache_key_normalizes_consistent():
    assert qa_cache_key(" 景泰蓝 工艺 ") == qa_cache_key("景泰蓝工艺")
    assert qa_cache_key("a").startswith(cache_mod.settings.redis_cache_prefix + ":")


# --------------------------------------------------------------------------- #
# Memory 后端
# --------------------------------------------------------------------------- #
class _FakeTime:
    """注入用时钟：now 可控推进，替代真实 time.time。"""

    def __init__(self):
        self.now = 1000.0

    def time(self):
        return self.now


@pytest.fixture()
def fake_time(monkeypatch):
    ft = _FakeTime()
    monkeypatch.setattr(cache_mod, "time", ft)
    return ft


def test_memory_set_get_roundtrip_preserves_identity(fake_time):
    import asyncio

    c = QaCache(backend="memory")
    obj = {"answer": "x"}
    asyncio.run(c.init_cache())
    asyncio.run(c.set_response("景泰蓝是什么", obj))
    got = asyncio.run(c.get_response("景泰蓝是什么"))
    assert got is obj  # 内存后端命中返同一引用（与原实现一致，零序列化）


def test_memory_normalization_hits_same_key(fake_time):
    import asyncio

    b = MemoryCacheBackend()
    asyncio.run(b.set(" 景泰蓝是什么  ", "v"))
    # 写入键与读取键的空白/大小写不同仍命中同一缓存项
    assert asyncio.run(b.get("景泰蓝  是什么")) == "v"
    assert len(b) == 1


def test_memory_ttl_expiry_evicts(fake_time, monkeypatch):
    import asyncio

    monkeypatch.setattr(cache_mod.settings, "cache_ttl_seconds", 100)
    b = MemoryCacheBackend()
    asyncio.run(b.set("q", "v"))
    assert asyncio.run(b.get("q")) == "v"
    fake_time.now += 101  # 超过 TTL
    assert asyncio.run(b.get("q")) is None


def test_memory_lru_evicts_oldest(fake_time, monkeypatch):
    import asyncio

    monkeypatch.setattr(cache_mod.settings, "cache_max_entries", 2)
    b = MemoryCacheBackend()
    asyncio.run(b.set("q1", 1))
    asyncio.run(b.set("q2", 2))
    asyncio.run(b.set("q3", 3))  # 超容量 → 淘汰最久未用的 q1
    assert len(b) == 2
    assert asyncio.run(b.get("q1")) is None
    assert asyncio.run(b.get("q3")) == 3


def test_memory_auto_probe_failure_falls_back(monkeypatch):
    import asyncio

    async def _no_redis():
        return None

    monkeypatch.setattr(cache_mod, "_try_redis", _no_redis)
    c = QaCache(backend="auto")
    asyncio.run(c.init_cache())
    assert isinstance(c.backend, MemoryCacheBackend)
    assert c.using_redis is False


# --------------------------------------------------------------------------- #
# Redis 后端
# --------------------------------------------------------------------------- #
def test_redis_roundtrip_via_json(monkeypatch):
    import asyncio

    stub = StubRedis()
    c = QaCache(backend="redis", redis_client=stub)
    asyncio.run(c.init_cache())
    asyncio.run(c.set_response("景泰蓝的掐丝工艺?", _Resp(answer="掐丝工艺", ts=7)))
    got = asyncio.run(c.get_response("景泰蓝的掐丝工艺?"))
    assert got == {"answer": "掐丝工艺", "ts": 7}  # Redis 侧为 dict（由 response_model 再校验）
    # key = prefix:sha1(normalize)，且带 TTL
    key = qa_cache_key("景泰蓝的掐丝工艺?")
    assert key in stub.snapshot()
    assert stub.ttls[key] == cache_mod.settings.cache_ttl_seconds


def test_redis_get_miss_returns_none():
    import asyncio

    c = QaCache(backend="redis", redis_client=StubRedis())
    assert asyncio.run(c.get_response("不存在的题")) is None


def test_redis_get_failure_treated_as_miss():
    import asyncio

    stub = StubRedis()
    stub.fail("get")
    c = QaCache(backend="redis", redis_client=stub)
    asyncio.run(c.init_cache())
    assert asyncio.run(c.get_response("q")) is None  # 不抛，当 miss


def test_redis_set_failure_swallowed():
    import asyncio

    stub = StubRedis()
    stub.fail("setex")
    c = QaCache(backend="redis", redis_client=stub)
    asyncio.run(c.init_cache())
    asyncio.run(c.set_response("q", _Resp(answer="a", ts=1)))  # 不抛
    assert asyncio.run(c.get_response("q")) is None
