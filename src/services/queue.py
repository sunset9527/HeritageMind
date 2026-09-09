"""Redis 音频转写任务队列（v1.4）

- 单 asyncio 客户端（redis.asyncio.from_url），与问答缓存共用同一 Redis。
- 队列 = List RPUSH/BLPOP；不做 ARQ/celery/fakeredis。
- push/pop 异常一律不抛：push 失败返回 False（API 侧仅 warning，worker 启动 sweep 兜底重入队），
  pop 失败/超时返回 None（worker 轮询循环继续）。
- 客户端懒加载：lifespan 需要时才真正建连，测试可注入内存桩（monkeypatch redis.asyncio.from_url）。
"""
import json
import logging
from typing import Any, Optional

from config import settings

logger = logging.getLogger(__name__)

_redis: Optional[Any] = None  # 懒加载客户端；redis.asyncio.Redis 或测试注入桩


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
    try:
        r = get_redis()
        payload = json.dumps({"media_id": int(media_id)})
        await r.rpush(settings.audio_queue_key, payload)
        return True
    except Exception as e:
        logger.warning(f"音频转写入队失败 media_id={media_id}: {e}")
        return False


async def pop_audio_job(timeout: int = 1) -> Optional[int]:
    """BLPOP 取一条任务，返回 media_id；空队列超时/异常返回 None。"""
    try:
        r = get_redis()
        item = await r.blpop([settings.audio_queue_key], timeout=timeout)
        if not item:  # (key, value) 或 None（超时）
            return None
        data = json.loads(item[1])
        return int(data.get("media_id"))
    except Exception as e:
        logger.warning(f"音频转写出队失败: {e}")
        return None
