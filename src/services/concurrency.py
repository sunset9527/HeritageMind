"""Bounded, observable permits for expensive in-process operations."""

from __future__ import annotations

import asyncio
import math
from contextlib import asynccontextmanager
from dataclasses import dataclass
from enum import StrEnum
from typing import Any, Mapping, Optional

from config import settings


class HighCostCapability(StrEnum):
    UPLOAD = "upload"
    DOCUMENT_PROCESSING = "document_processing"
    INDEX_REBUILD = "index_rebuild"
    SERVER_LLM = "server_llm"
    AUDIO_TRANSCRIPTION = "audio_transcription"
    RETRIEVAL = "retrieval"


class ConcurrencyBusyError(RuntimeError):
    """No permit became available inside the deliberately short wait window."""

    def __init__(self, capability: HighCostCapability, retry_after: int):
        self.capability = capability
        self.retry_after = retry_after
        super().__init__(f"{capability.value} is busy")


@dataclass(frozen=True)
class ConcurrencySnapshot:
    current: int
    maximum: int
    rejected: int


@dataclass
class _Pool:
    maximum: int
    semaphore: asyncio.Semaphore
    current: int = 0
    rejected: int = 0


def limits_from_settings(source: Any = settings) -> dict[HighCostCapability, int]:
    return {
        HighCostCapability.UPLOAD: source.upload_concurrency_limit,
        HighCostCapability.DOCUMENT_PROCESSING: source.document_processing_concurrency_limit,
        HighCostCapability.INDEX_REBUILD: source.index_rebuild_concurrency_limit,
        HighCostCapability.SERVER_LLM: source.server_llm_concurrency_limit,
        HighCostCapability.AUDIO_TRANSCRIPTION: source.audio_transcription_concurrency_limit,
        HighCostCapability.RETRIEVAL: source.retrieval_concurrency_limit,
    }


class ConcurrencyLimiter:
    """Independent semaphore pools.  A cancelled or failing holder always releases."""

    def __init__(
        self,
        *,
        limits: Optional[Mapping[HighCostCapability, int]] = None,
        acquire_timeout_seconds: Optional[float] = None,
    ):
        configured = dict(limits or limits_from_settings())
        self._acquire_timeout_seconds = (
            settings.high_cost_acquire_timeout_seconds
            if acquire_timeout_seconds is None
            else acquire_timeout_seconds
        )
        if self._acquire_timeout_seconds <= 0:
            raise ValueError("acquire_timeout_seconds must be positive")
        self._pools: dict[HighCostCapability, _Pool] = {}
        for capability in HighCostCapability:
            maximum = int(configured[capability])
            if maximum <= 0:
                raise ValueError(f"{capability.value} limit must be positive")
            self._pools[capability] = _Pool(maximum, asyncio.Semaphore(maximum))

    def snapshot(self, capability: HighCostCapability) -> ConcurrencySnapshot:
        pool = self._pools[HighCostCapability(capability)]
        return ConcurrencySnapshot(pool.current, pool.maximum, pool.rejected)

    @asynccontextmanager
    async def permit(self, capability: HighCostCapability):
        capability = HighCostCapability(capability)
        pool = self._pools[capability]
        acquired = False
        try:
            try:
                await asyncio.wait_for(pool.semaphore.acquire(), self._acquire_timeout_seconds)
                acquired = True
                pool.current += 1
            except TimeoutError as exc:
                pool.rejected += 1
                raise ConcurrencyBusyError(
                    capability, max(1, math.ceil(self._acquire_timeout_seconds))
                ) from exc
            yield
        finally:
            if acquired:
                pool.current -= 1
                pool.semaphore.release()


_concurrency_limiter: Optional[ConcurrencyLimiter] = None


def get_concurrency_limiter() -> ConcurrencyLimiter:
    global _concurrency_limiter
    if _concurrency_limiter is None:
        _concurrency_limiter = ConcurrencyLimiter()
    return _concurrency_limiter


def reset_concurrency_limiter() -> None:
    global _concurrency_limiter
    _concurrency_limiter = None
