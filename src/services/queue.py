"""Redis 音频转写任务队列（v1.4）

- 单 asyncio 客户端（redis.asyncio.from_url），与问答缓存共用同一 Redis。
- 队列 = List RPUSH/BLPOP；不做 ARQ/celery/fakeredis。
- push/pop 异常一律不抛：push 失败返回 False（API 侧仅 warning，worker 启动 sweep 兜底重入队），
  pop 失败/超时返回 None（worker 轮询循环继续）。
- 客户端懒加载：lifespan 需要时才真正建连，测试可注入内存桩（monkeypatch redis.asyncio.from_url）。
"""
import json
import logging
from dataclasses import dataclass
from typing import Any, Optional

from config import settings

logger = logging.getLogger(__name__)

_redis: Optional[Any] = None  # 懒加载客户端；redis.asyncio.Redis 或测试注入桩
_TASK_VERSION = 1
_TASK_KINDS = frozenset(
    {"document", "audio", "knowledge_index", "image_index", "audio_index"}
)


@dataclass(frozen=True)
class TaskEnvelope:
    version: int
    kind: str
    entity_id: int


def _decode_task(payload: str) -> TaskEnvelope | None:
    try:
        data = json.loads(payload)
        version = int(data["version"])
        kind = str(data["kind"])
        entity_id = int(data["entity_id"])
    except (KeyError, TypeError, ValueError, json.JSONDecodeError):
        logger.warning("丢弃格式无效的后台任务消息")
        return None
    if version != _TASK_VERSION or kind not in _TASK_KINDS or entity_id < 1:
        logger.warning("丢弃不支持的后台任务消息 version=%s kind=%s", version, kind)
        return None
    return TaskEnvelope(version=version, kind=kind, entity_id=entity_id)


async def _push_task(kind: str, entity_id: int, queue_key: str) -> bool:
    if kind not in _TASK_KINDS or int(entity_id) < 1:
        logger.warning("拒绝无效后台任务 kind=%s entity_id=%s", kind, entity_id)
        return False
    try:
        payload = {
            "version": _TASK_VERSION,
            "kind": kind,
            "entity_id": int(entity_id),
        }
        if kind == "audio":
            payload["media_id"] = int(entity_id)  # 旧观测/日志兼容字段
        await get_redis().rpush(queue_key, json.dumps(payload))
        return True
    except Exception as exc:
        logger.warning("后台任务入队失败 kind=%s entity_id=%s: %s", kind, entity_id, exc)
        return False


async def _pop_task(queue_key: str, timeout: int) -> TaskEnvelope | None:
    try:
        item = await get_redis().blpop([queue_key], timeout=timeout)
        if not item:
            return None
        return _decode_task(item[1])
    except Exception as exc:
        logger.warning("后台任务出队失败: %s", exc)
        return None


async def push_job(kind: str, entity_id: int) -> bool:
    return await _push_task(kind, entity_id, settings.task_queue_key)


async def pop_job(timeout: int = 1) -> TaskEnvelope | None:
    return await _pop_task(settings.task_queue_key, timeout)


def get_redis() -> Any:
    """懒加载 redis.asyncio 客户端（连接在首次命令时才真正建立）。"""
    global _redis
    if _redis is None:
        import redis.asyncio as aioredis  # noqa: PLC0415  # lazy import

        _redis = aioredis.from_url(
            settings.redis_url,
            decode_responses=True,
            socket_connect_timeout=1,
            socket_timeout=3,
        )
    return _redis


async def close_redis() -> None:
    """关闭并清空懒加载客户端（应用关闭 / 连接探测失败时）。"""
    global _redis
    if _redis is not None:
        try:
            await _redis.aclose()
        except Exception as e:
            logger.warning(f"关闭 Redis 连接失败: {e}")
        _redis = None


async def push_audio_job(media_id: int) -> bool:
    """入队一条转写任务。成功 True；Redis 不可达/异常记 warning 返回 False（调用方不阻断）。"""
    return await _push_task("audio", media_id, settings.audio_queue_key)


async def pop_audio_job(timeout: int = 1) -> Optional[int]:
    """BLPOP 取一条任务，返回 media_id；空队列超时/异常返回 None。"""
    task = await _pop_task(settings.audio_queue_key, timeout)
    if task is None or task.kind != "audio":
        return None
    return task.entity_id
