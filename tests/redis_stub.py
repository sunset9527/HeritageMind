"""redis.asyncio.Redis 的内存桩（零网络离线测试用）。

覆盖本项目用到的子集：ping / rpush / blpop / get / setex / aclose。
- `fail(*ops)`：让指定操作抛 ConnectionError，模拟 Redis 不可达/抖动。
- list 为 FIFO（RPUSH 尾插、BLPOP 头取）；store 为简单 kv。
"""


class StubRedis:
    def __init__(self):
        self.lists = {}
        self.store = {}
        self.ttls = {}
        self.closed = False
        self._fail_ops = set()

    def fail(self, *ops):
        """让给定操作抛出连接异常（模拟故障）。"""
        self._fail_ops.update(ops)

    def _guard(self, op):
        if op in self._fail_ops:
            raise ConnectionError(f"stub {op} forced failure")

    async def ping(self):
        self._guard("ping")
        return True

    async def rpush(self, key, value):
        self._guard("rpush")
        self.lists.setdefault(key, []).append(value)
        return len(self.lists[key])

    async def blpop(self, keys, timeout=0):
        self._guard("blpop")
        if isinstance(keys, str):
            keys = [keys]
        for key in keys:
            lst = self.lists.get(key)
            if lst:
                return (key, lst.pop(0))
        return None  # 模拟空队列超时

    async def get(self, key):
        self._guard("get")
        return self.store.get(key)

    async def setex(self, key, ttl, value):
        self._guard("setex")
        self.store[key] = value
        self.ttls[key] = ttl
        return True

    async def aclose(self):
        self.closed = True

    def snapshot(self):
        return dict(self.store)
