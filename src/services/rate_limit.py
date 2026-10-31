"""业务限流：Redis 原子固定窗口；生产 Redis 故障时拒绝受保护请求。

Redis key 始终只包含类别和 SHA-256 截断摘要。原始用户 ID、账号、IP、JWT、
API Key 或问题正文均不会进入 key、返回值或日志。
"""

from __future__ import annotations

import hmac
import logging
import math
import time
from collections import OrderedDict
from dataclasses import dataclass
from enum import StrEnum
from threading import Lock
from typing import Any, Callable, Mapping, Optional

from config import settings
from src.middleware.request_context import ClientIdentity

logger = logging.getLogger(__name__)


class RateLimitCategory(StrEnum):
    REGISTRATION = "registration"
    LOGIN = "login"
    ANONYMOUS_QUERY = "anonymous_query"
    AUTHENTICATED_QUERY = "authenticated_query"
    AI_SEARCH = "ai_search"
    UPLOAD = "upload"
    INDEX_REBUILD = "index_rebuild"
    READ_ONLY = "read_only"


@dataclass(frozen=True)
class RateLimitPolicy:
    limit: int
    window_seconds: int


@dataclass(frozen=True)
class RateLimitDecision:
    allowed: bool
    count: int
    remaining: int
    retry_after: int
    source: str
    available: bool = True


@dataclass
class _MemoryBucket:
    count: int
    started_at: float


# EVAL makes increment + initial expiry a single Redis operation across workers.
_FIXED_WINDOW_LUA = """
local highest = 0
local retry_ttl = 0
for _, key in ipairs(KEYS) do
  local current = redis.call('INCR', key)
  if current == 1 then
    redis.call('EXPIRE', key, ARGV[1])
  end
  local ttl = redis.call('TTL', key)
  if current > highest then highest = current end
  if ttl > retry_ttl then retry_ttl = ttl end
end
return {highest, retry_ttl}
"""


def policies_from_settings(source: Any = settings) -> dict[RateLimitCategory, RateLimitPolicy]:
    """Build the explicit business policy map; anonymous policy exists even if route use is disabled."""
    return {
        RateLimitCategory.REGISTRATION: RateLimitPolicy(source.registration_quota, source.registration_window_seconds),
        RateLimitCategory.LOGIN: RateLimitPolicy(source.login_quota, source.login_window_seconds),
        RateLimitCategory.ANONYMOUS_QUERY: RateLimitPolicy(source.anonymous_query_quota, source.anonymous_query_window_seconds),
        RateLimitCategory.AUTHENTICATED_QUERY: RateLimitPolicy(source.authenticated_query_quota, source.authenticated_query_window_seconds),
        RateLimitCategory.AI_SEARCH: RateLimitPolicy(source.ai_search_quota, source.ai_search_window_seconds),
        RateLimitCategory.UPLOAD: RateLimitPolicy(source.upload_quota, source.upload_window_seconds),
        RateLimitCategory.INDEX_REBUILD: RateLimitPolicy(source.index_rebuild_quota, source.index_rebuild_window_seconds),
        RateLimitCategory.READ_ONLY: RateLimitPolicy(source.readonly_quota, source.readonly_window_seconds),
    }


class RateLimiter:
    """Redis-first limiter; dev/test may use a bounded local fallback.

    ``redis_client`` is deliberately injectable. Production gets its lazy client through
    :func:`get_rate_limiter`; tests need no Redis server or wall-clock sleeps.
    """

    def __init__(
        self,
        *,
        redis_client: Any = None,
        redis_provider: Optional[Callable[[], Any]] = None,
        policies: Optional[Mapping[RateLimitCategory, RateLimitPolicy]] = None,
        clock: Callable[[], float] = time.monotonic,
        memory_max_keys: Optional[int] = None,
        key_prefix: str = "heritagemind:rate:v1",
        app_env: Optional[str] = None,
        hmac_key: Optional[str] = None,
        hmac_previous_keys: Optional[list[str]] = None,
    ):
        self._redis_client = redis_client
        self._redis_provider = redis_provider
        self._policies = dict(policies or policies_from_settings())
        self._clock = clock
        self._memory_max_keys = memory_max_keys or settings.rate_limit_memory_max_keys
        self._key_prefix = key_prefix
        self._app_env = app_env or settings.app_env
        current_hmac_key = hmac_key if hmac_key is not None else settings.rate_limit_hmac_key
        previous_hmac_keys = (
            hmac_previous_keys
            if hmac_previous_keys is not None
            else settings.rate_limit_hmac_previous_keys
        )
        self._hmac_keys = tuple(dict.fromkeys(
            key for key in (current_hmac_key, *previous_hmac_keys) if key
        ))
        if not self._hmac_keys:
            raise ValueError("rate limit HMAC key must not be empty")
        self._memory: OrderedDict[str, _MemoryBucket] = OrderedDict()
        self._memory_lock = Lock()

    @property
    def memory_key_count(self) -> int:
        return len(self._memory)

    def _policy(self, category: RateLimitCategory) -> RateLimitPolicy:
        return self._policies[RateLimitCategory(category)]

    @staticmethod
    def _identity_material(
        *, user_id: Any = None, account_identifier: Optional[str] = None, identity: Optional[ClientIdentity] = None
    ) -> str:
        # User identity has priority for authenticated business calls. Login and
        # registration callers intentionally pass account_identifier instead.
        if user_id is not None:
            return f"user:{user_id}"
        if account_identifier is not None:
            return f"account:{account_identifier.strip().casefold()}"
        client_ip = identity.client_ip if identity is not None else "unknown"
        return f"ip:{client_ip}"

    def _key_for_secret(
        self,
        category: RateLimitCategory,
        secret: str,
        *,
        user_id: Any = None,
        account_identifier: Optional[str] = None,
        identity: Optional[ClientIdentity] = None,
    ) -> str:
        material = self._identity_material(
            user_id=user_id, account_identifier=account_identifier, identity=identity
        )
        digest = hmac.new(secret.encode("utf-8"), material.encode("utf-8"), "sha256").hexdigest()[:24]
        return f"{self._key_prefix}:{RateLimitCategory(category).value}:{digest}"

    def key_for(
        self,
        category: RateLimitCategory,
        *,
        user_id: Any = None,
        account_identifier: Optional[str] = None,
        identity: Optional[ClientIdentity] = None,
    ) -> str:
        """Return the current HMAC-keyed storage key (never an unhashed subject)."""
        return self._key_for_secret(
            category,
            self._hmac_keys[0],
            user_id=user_id,
            account_identifier=account_identifier,
            identity=identity,
        )

    def _keys_for(
        self,
        category: RateLimitCategory,
        *,
        user_id: Any = None,
        account_identifier: Optional[str] = None,
        identity: Optional[ClientIdentity] = None,
    ) -> tuple[str, ...]:
        # During secret rotation, incrementing old and current keys in one Lua
        # transaction preserves the existing window until old keys are removed.
        return tuple(
            self._key_for_secret(
                category,
                secret,
                user_id=user_id,
                account_identifier=account_identifier,
                identity=identity,
            )
            for secret in self._hmac_keys
        )

    def _redis(self) -> Any:
        return self._redis_client if self._redis_client is not None else self._redis_provider()

    async def check(
        self,
        category: RateLimitCategory,
        *,
        user_id: Any = None,
        account_identifier: Optional[str] = None,
        identity: Optional[ClientIdentity] = None,
    ) -> RateLimitDecision:
        category = RateLimitCategory(category)
        policy = self._policy(category)
        keys = self._keys_for(
            category,
            user_id=user_id,
            account_identifier=account_identifier,
            identity=identity,
        )
        try:
            raw = await self._redis().eval(_FIXED_WINDOW_LUA, len(keys), *keys, policy.window_seconds)
            count, ttl = int(raw[0]), int(raw[1])
            return self._decision(count, ttl, policy, source="redis")
        except Exception as exc:
            # Do not leak a Redis endpoint/error through the HTTP response or key logs.
            logger.warning("rate_limit_redis_failed category=%s error=%s", category.value, type(exc).__name__)
            if self._app_env == "prod":
                # A per-worker fallback cannot preserve a distributed quota. Production
                # must fail closed rather than silently granting requests on each worker.
                return RateLimitDecision(False, 0, 0, 1, source="unavailable", available=False)
            return self._check_memory(keys, policy)

    @staticmethod
    def _decision(count: int, ttl: int, policy: RateLimitPolicy, *, source: str) -> RateLimitDecision:
        return RateLimitDecision(
            allowed=count <= policy.limit,
            count=count,
            remaining=max(policy.limit - count, 0),
            retry_after=max(ttl, 1),
            source=source,
        )

    def _evict_expired(self, now: float) -> None:
        for key, bucket in list(self._memory.items()):
            # ``>=`` matches expiry at the precise start of a new fixed window.
            if now - bucket.started_at >= self._memory_policy_window_from_key(key):
                self._memory.pop(key, None)

    def _memory_policy_window_from_key(self, key: str) -> int:
        # The category is controlled internally, never user supplied. This avoids
        # retaining plaintext identities while allowing expiry sweep per policy.
        category_text = key.rsplit(":", 2)[-2]
        return self._policy(RateLimitCategory(category_text)).window_seconds

    def _check_memory(self, keys: tuple[str, ...], policy: RateLimitPolicy) -> RateLimitDecision:
        # No await inside this critical section: sweep, capacity admission and
        # increments must be indivisible across threads using one process.
        with self._memory_lock:
            now = self._clock()
            self._evict_expired(now)
            missing = [key for key in keys if key not in self._memory]
            if len(self._memory) + len(missing) > self._memory_max_keys:
                # Never evict an active identity: that would reset its quota and make
                # overload bypassable by cycling identities. Expired buckets were
                # already swept above; only a new identity is rejected here.
                return RateLimitDecision(
                    False,
                    policy.limit + 1,
                    0,
                    1,
                    source="memory_capacity",
                )
            counts = []
            ttls = []
            for key in keys:
                bucket = self._memory.get(key)
                if bucket is None:
                    bucket = _MemoryBucket(count=0, started_at=now)
                    self._memory[key] = bucket
                bucket.count += 1
                self._memory.move_to_end(key)
                counts.append(bucket.count)
                ttls.append(max(1, math.ceil(policy.window_seconds - (now - bucket.started_at))))
            # This quota is only meaningful inside one process; production never uses it.
            return self._decision(max(counts), max(ttls), policy, source="memory")


_rate_limiter: Optional[RateLimiter] = None


def get_rate_limiter() -> RateLimiter:
    global _rate_limiter
    if _rate_limiter is None:
        from src.services.queue import get_redis  # lazy: no Redis import/config work at module import

        _rate_limiter = RateLimiter(redis_provider=get_redis)
    return _rate_limiter


def reset_rate_limiter() -> None:
    global _rate_limiter
    _rate_limiter = None
