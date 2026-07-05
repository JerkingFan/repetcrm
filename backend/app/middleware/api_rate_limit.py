"""Global API rate limiting (Redis sliding window + in-memory fallback)."""

from __future__ import annotations

import logging
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from app.config import Settings, get_settings
from app.services.auth_rate_limit import RedisSlidingWindowLimiter

logger = logging.getLogger(__name__)

_SKIP_PREFIXES = ("/webhooks/",)
_SKIP_PATHS = frozenset({"/health", "/metrics", "/docs", "/redoc", "/openapi.json"})

_limiter: RedisSlidingWindowLimiter | None = None


def _client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for", "")
    if forwarded:
        return forwarded.split(",")[0].strip() or "unknown"
    if request.client:
        return request.client.host
    return "unknown"


def _get_limiter(cfg: Settings) -> RedisSlidingWindowLimiter:
    global _limiter
    if _limiter is None:
        _limiter = RedisSlidingWindowLimiter(
            cfg.api_rate_limit_max,
            cfg.api_rate_limit_window_sec,
            prefix="api:global",
        )
    return _limiter


class ApiRateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app):
        super().__init__(app)

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        cfg = get_settings()
        if not cfg.api_rate_limit_enabled:
            return await call_next(request)

        path = request.url.path
        if (
            path in _SKIP_PATHS
            or path.startswith("/boards/ws/")
            or any(path.startswith(p) for p in _SKIP_PREFIXES)
        ):
            return await call_next(request)

        ip = _client_ip(request)
        limiter = _get_limiter(cfg)
        if limiter.is_blocked(ip):
            retry = limiter.retry_after_sec(ip)
            logger.warning("api_rate_limited ip=%s path=%s retry_after=%s", ip, path, retry)
            return Response(
                status_code=429,
                content='{"detail":"Too many requests"}',
                media_type="application/json",
                headers={"Retry-After": str(retry)},
            )

        limiter.record(ip)
        return await call_next(request)
