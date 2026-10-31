"""FastAPI adapter for high-cost concurrency permits."""

from __future__ import annotations

from fastapi import HTTPException, status

from src.services.concurrency import (
    ConcurrencyBusyError,
    HighCostCapability,
    get_concurrency_limiter,
)


def high_cost_limit(capability: HighCostCapability):
    """Yield dependency that holds a capability permit for the route lifetime."""
    async def dependency():
        try:
            async with get_concurrency_limiter().permit(capability):
                yield
        except ConcurrencyBusyError as exc:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail={"code": "busy", "message": "服务繁忙，请稍后重试"},
                headers={"Retry-After": str(exc.retry_after)},
            ) from exc

    dependency.concurrency_capability = capability
    return dependency
