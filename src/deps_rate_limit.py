"""FastAPI adapters for business rate limiting; authorization remains separate."""

from __future__ import annotations

from typing import Any, Optional

from fastapi import Depends, HTTPException, status

from src.deps import get_optional_user
from src.middleware.request_context import get_client_identity
from src.services.rate_limit import RateLimitCategory, get_rate_limiter


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
    if not decision.allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={"code": "rate_limit_exceeded", "message": "请求过于频繁，请稍后再试"},
            headers={"Retry-After": str(decision.retry_after)},
        )


def rate_limit(
    category: RateLimitCategory,
    *,
    authenticated_category: Optional[RateLimitCategory] = None,
):
    """Return a route dependency. It limits, but never authenticates or authorizes."""
    async def dependency(current_user: Optional[Any] = Depends(get_optional_user)) -> None:
        selected = authenticated_category if current_user is not None and authenticated_category else category
        await enforce_rate_limit(selected, current_user=current_user)

    return dependency
