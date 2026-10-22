"""统一上传/维护任务信封与旧音频队列兼容包装器。"""

import asyncio
import json

from src.services import queue
from tests.redis_stub import StubRedis


def test_generic_queue_round_trips_versioned_envelope(monkeypatch):
    stub = StubRedis()
    monkeypatch.setattr(queue, "_redis", stub)

    assert asyncio.run(queue.push_job("document", 42)) is True
    task = asyncio.run(queue.pop_job(timeout=0))

    assert task.version == 1
    assert task.kind == "document"
    assert task.entity_id == 42


def test_generic_queue_drops_unknown_or_malformed_message(monkeypatch):
    stub = StubRedis()
    monkeypatch.setattr(queue, "_redis", stub)
    stub.lists[queue.settings.task_queue_key] = [
        json.dumps({"version": 1, "kind": "unknown", "entity_id": 1}),
        "not-json",
    ]

    assert asyncio.run(queue.pop_job(timeout=0)) is None
    assert asyncio.run(queue.pop_job(timeout=0)) is None


def test_audio_compatibility_wrapper_uses_generic_envelope(monkeypatch):
    stub = StubRedis()
    monkeypatch.setattr(queue, "_redis", stub)

    assert asyncio.run(queue.push_audio_job(7)) is True
    assert asyncio.run(queue.pop_audio_job(timeout=0)) == 7
