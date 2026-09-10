"""v1.4 Redis 转写队列测试（离线：直接注入内存桩到 queue._redis，不建真实连接）。"""
import pytest

from src.services import queue
from src.services.queue import close_redis, get_redis, pop_audio_job, push_audio_job
from tests.redis_stub import StubRedis


@pytest.fixture()
def stub(monkeypatch):
    s = StubRedis()
    monkeypatch.setattr(queue, "_redis", s)  # 绕过 from_url，直接注入桩
    return s


def test_get_redis_returns_shared_client(stub):
    assert get_redis() is stub


def test_push_pop_fifo_order(stub):
    import asyncio

    for i in (1, 2, 3):
        assert asyncio.run(push_audio_job(i)) is True
    assert asyncio.run(pop_audio_job(timeout=0)) == 1
    assert asyncio.run(pop_audio_job(timeout=0)) == 2
    assert asyncio.run(pop_audio_job(timeout=0)) == 3


def test_pop_empty_returns_none(stub):
    import asyncio

    assert asyncio.run(pop_audio_job(timeout=0)) is None


def test_queue_key_used(stub):
    import asyncio

    asyncio.run(push_audio_job(42))
    assert queue.settings.audio_queue_key in stub.lists
    payload = stub.lists[queue.settings.audio_queue_key][0]
    assert '"media_id"' in payload and "42" in payload  # JSON 序列化入队


def test_push_failure_returns_false(stub):
    import asyncio

    stub.fail("rpush")
    assert asyncio.run(push_audio_job(1)) is False  # 不抛，调用方仅 warning


def test_pop_failure_returns_none(stub):
    import asyncio

    stub.fail("blpop")
    assert asyncio.run(pop_audio_job(timeout=1)) is None


def test_close_redis_closes_and_resets(stub):
    import asyncio

    asyncio.run(close_redis())
    assert stub.closed is True
    assert queue._redis is None


def test_real_redis_roundtrip_if_reachable():
    """选装：真实 Redis 可达时验证 RPUSH/BLPOP；不可达直接跳过（不要求环境）。

    同一事件循环内完成 ping/push/pop/close，避免连接池跨 asyncio.run 绑到已关闭 loop。
    """
    import asyncio
    import uuid

    async def _run():
        try:
            await get_redis().ping()
        except Exception:
            return "SKIP"
        old = queue.settings.audio_queue_key
        queue.settings.audio_queue_key = f"heritagemind:test:queue:{uuid.uuid4().hex[:8]}"
        try:
            ok = await push_audio_job(77)
            return (await pop_audio_job(timeout=2)) if ok else None
        finally:
            queue.settings.audio_queue_key = old
            await close_redis()

    result = asyncio.run(_run())
    if result == "SKIP":
        pytest.skip("真实 Redis 不可达，跳过集成用例")
    assert result == 77
