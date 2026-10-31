"""FastAPI adapters for business rate limiting; authorization remains separate."""

from __future__ import annotations

from typing import Any, Optional

from fastapi import Depends, HTTPException, status

from src.deps import get_optional_user
from src.middleware.request_context import get_client_identity
from src.services.rate_limit import RateLimitCategory, get_rate_limiter


def _raise_for_rate_limit_decision(decision) -> None:
    """Convert internal storage decisions to the stable external contract."""
    if not decision.available:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"code": "rate_limit_unavailable", "message": "服务繁忙，请稍后再试"},
            headers={"Retry-After": str(decision.retry_after)},
        )
    if not decision.allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={"code": "rate_limit_exceeded", "message": "请求过于频繁，请稍后再试"},
            headers={"Retry-After": str(decision.retry_after)},
        )


async def enforce_rate_limit(
    category: RateLimitCategory,
    *,
    current_user: Optional[Any] = None,
    account_identifier: Optional[str] = None,
) -> None:
    """Check once and expose only stable client-facing overload information."""
    decision = await get_rate_limiter().check(
        category,
        user_id=getattr(current_user, "id", None),
        account_identifier=account_identifier,
        identity=get_client_identity(),
    )
    _raise_for_rate_limit_decision(decision)


async def enforce_account_and_ip_rate_limits(
    category: RateLimitCategory,
    account_identifier: str,
) -> None:
    """Protect credential endpoints by both normalized account and trusted client IP.

    The account alone is user-controlled, so a caller must pass both independent
    buckets. Any unavailable or exhausted bucket rejects the request.
    """
    limiter = get_rate_limiter()
    account_decision = await limiter.check(category, account_identifier=account_identifier)
    _raise_for_rate_limit_decision(account_decision)
    ip_decision = await limiter.check(category, identity=get_client_identity())
    _raise_for_rate_limit_decision(ip_decision)


def rate_limit(
    category: RateLimitCategory,
    *,
    authenticated_category: Optional[RateLimitCategory] = None,
):
    """Return a route dependency. It limits, but never authenticates or authorizes."""
    async def dependency(current_user: Optional[Any] = Depends(get_optional_user)) -> None:
        selected = authenticated_category if current_user is not None and authenticated_category else category
        await enforce_rate_limit(selected, current_user=current_user)

    # Expose policy metadata for route-contract tests; this is not client input.
    dependency.rate_limit_category = category
    return dependency
