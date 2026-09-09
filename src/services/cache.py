"""热门问答缓存（v1.4）：进程内 LRU + 可选 Redis 后端

- 语义迁移自 api.py 原内联 `_normalize_question/_get_cached_response/_set_cached_response`：
  问题先归一化（去空白+小写），命中且未过期返回，写时按 `cache_max_entries` LRU 淘汰。
- `MemoryCacheBackend`：OrderedDict LRU + TTL，淘汰规则与原实现逐条对齐（存原始对象，命中返同一引用）。
- `RedisCacheBackend`：key = `qa_cache_key(question)`；值 JSON 序列化（pydantic v2 `model_dump(mode="json")`）。
  Redis 读/写异常一律降级：get→None（当 miss）、set→吞掉记 warning，保证缓存故障不影响问答。
- `QaCache`：按 `settings.cache_backend`（auto/redis/memory）选后端；auto 用 `init_cache()` 探测 Redis 可达性，
  不可达自动落回进程内 LRU。get/set 统一 async 接口。

备注：内存后端存 QueryResponse 对象本身（与原实现一致，命中零序列化开销）；Redis 后端只能存 JSON
（跨进程/重启共享），取回为 dict，由 FastAPI response_model 重新校验为 QueryResponse。
"""
import hashlib
import json
import logging
import time
from collections import OrderedDict
from typing import Any, Optional

from config import settings

logger = logging.getLogger(__name__)


# --------------------------------------------------------------------------- #
# key / 序列化
# --------------------------------------------------------------------------- #
def _normalize_question(question: str) -> str:
    """问题归一化：去除所有空白字符 + 转小写（语义同 api.py 原实现，迁移后旧命中不变）。"""
    return "".join(question.split()).lower()


def qa_cache_key(question: str) -> str:
    """Redis key：`{prefix}:sha1(normalize(question))`——定长且避免空白/中文等非法字符。"""
    digest = hashlib.sha1(_normalize_question(question).encode("utf-8")).hexdigest()
    return f"{settings.redis_cache_prefix}:{digest}"


def _serialize(value: Any) -> str:
    """pydantic v2 对象用 model_dump(mode='json') 保证可 JSON 化（datetime→ISO str）；dict/原始类型兜底。"""
    dumper = getattr(value, "model_dump", None)
    if callable(dumper):
        return json.dumps(dumper(mode="json"), ensure_ascii=False)
    return json.dumps(value, ensure_ascii=False, default=str)


def _deserialize(raw: str) -> Any:
    try:
        return json.loads(raw)
    except Exception:
        return None


# --------------------------------------------------------------------------- #
# 内存后端
# --------------------------------------------------------------------------- #
class MemoryCacheBackend:
    """OrderedDict LRU + TTL，语义与原 api.py:71-102 内联实现一致。"""

    def __init__(self, max_entries: Optional[int] = None, ttl_seconds: Optional[int] = None):
        self._data: "OrderedDict[str, tuple]" = OrderedDict()
        self.max_entries = max_entries if max_entries is not None else settings.cache_max_entries
        self.ttl = ttl_seconds if ttl_seconds is not None else settings.cache_ttl_seconds

    async def get(self, question: str) -> Optional[Any]:
        key = _normalize_question(question)
        item = self._data.get(key)
        if item is None:
            return None
        value, timestamp = item
        if time.time() - timestamp > self.ttl:
            self._data.pop(key, None)
            return None
        self._data.move_to_end(key)  # 命中刷新 LRU 顺序
        return value

    async def set(self, question: str, value: Any) -> None:
        key = _normalize_question(question)
        self._data[key] = (value, time.time())
        self._data.move_to_end(key)
        while len(self._data) > self.max_entries:  # LRU 淘汰最久未用（队首）
            self._data.popitem(last=False)

    def clear(self) -> None:
        self._data.clear()

    def __len__(self) -> int:
        return len(self._data)


# --------------------------------------------------------------------------- #
# Redis 后端
# --------------------------------------------------------------------------- #
class RedisCacheBackend:
    """Redis SETEX/GET 后端：TTL 由 Redis 侧保证，无需淘汰逻辑。

    redis_client 注入点：可为 redis.asyncio.Redis，也可为满足 get/setex 的测试桩。
    """

    def __init__(self, redis_client: Any):
        self._redis = redis_client

    async def get(self, question: str) -> Optional[Any]:
        try:
            raw = await self._redis.get(qa_cache_key(question))
        except Exception as e:
            logger.warning(f"Redis 缓存读失败，按 miss 处理: {e}")
            return None
        if raw is None:
            return None
        return _deserialize(raw)

    async def set(self, question: str, value: Any) -> None:
        try:
            await self._redis.setex(qa_cache_key(question), settings.cache_ttl_seconds, _serialize(value))
        except Exception as e:
            logger.warning(f"Redis 缓存写失败（忽略，不影响问答）: {e}")


# --------------------------------------------------------------------------- #
# 门面
# --------------------------------------------------------------------------- #
async def _try_redis() -> Any:
    """连接一次并 ping；失败返回 None（同时关闭连接）。避免顶层 import 循环：queue 在调用时引入。"""
    from src.services.queue import close_redis, get_redis  # noqa: PLC0415  # lazy import

    r = get_redis()
    try:
        await r.ping()
        return r
    except Exception as e:
        logger.info(f"Redis 不可达，问答缓存降级进程内 LRU: {e}")
        close_redis()
        return None


class QaCache:
    """问答缓存门面：按 backend 选实现；后端未初始化时惰性 init。"""

    def __init__(self, backend: Optional[str] = None, redis_client: Optional[Any] = None):
        # backend 显式传可覆盖 settings.cache_backend（测试注入）；redis_client 供测试注入桩
        self._backend_name = backend or settings.cache_backend
        self._injected_client = redis_client
        self.backend: Optional[Any] = None
        self.using_redis = False

    async def init_cache(self) -> None:
        if self.backend is not None:
            return
        name = self._backend_name
        if name == "memory":
            self.backend = MemoryCacheBackend()
            logger.info("问答缓存后端: memory（配置指定）")
            return
        client = self._injected_client
        if client is None:
            client = await _try_redis()
        if client is not None:
            self.backend = RedisCacheBackend(client)
            self.using_redis = True
            logger.info("问答缓存后端: redis")
        else:
            if name == "redis":
                logger.warning("cache_backend=redis 但 Redis 不可达，降级进程内 LRU")
            else:
                logger.info("问答缓存后端: memory（Redis 不可达降级）")
            self.backend = MemoryCacheBackend()

    async def get_response(self, question: str) -> Optional[Any]:
        if self.backend is None:
            await self.init_cache()
        return await self.backend.get(question)

    async def set_response(self, question: str, value: Any) -> None:
        if self.backend is None:
            await self.init_cache()
        await self.backend.set(question, value)

    def reset(self) -> None:
        self.backend = None
        self.using_redis = False


# 进程级单例（api.py lifespan 初始化后 /query 复用）
_qa_cache: Optional[QaCache] = None


def get_qa_cache() -> QaCache:
    global _qa_cache
    if _qa_cache is None:
        _qa_cache = QaCache()
    return _qa_cache


def reset_qa_cache() -> None:
    global _qa_cache
    _qa_cache = None
