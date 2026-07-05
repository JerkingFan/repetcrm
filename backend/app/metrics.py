"""Prometheus metrics and HTTP request instrumentation."""

from __future__ import annotations

import logging
import time
from typing import Callable

from fastapi import FastAPI, Request, Response
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Gauge, Histogram, generate_latest
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.routing import Match

from app.config import Settings
from app.redis_client import get_redis
from app.services.db_startup import count_users

logger = logging.getLogger(__name__)

HTTP_REQUESTS = Counter(
    "http_requests_total",
    "Total HTTP requests",
    ["method", "path", "status"],
)
HTTP_DURATION = Histogram(
    "http_request_duration_seconds",
    "HTTP request latency",
    ["method", "path"],
    buckets=(0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0),
)
APP_USERS = Gauge("repetcrm_users_total", "Registered tutor accounts")
APP_REDIS = Gauge("repetcrm_redis_up", "Redis connectivity (1=up, 0=disabled/down)")
APP_INFO = Gauge(
    "repetcrm_info",
    "Application build info",
    ["version", "env"],
)


def _route_path(request: Request) -> str:
    for route in request.app.routes:
        match, _ = route.matches(request.scope)
        if match == Match.FULL:
            return getattr(route, "path", request.url.path)
    return request.url.path


class MetricsMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        if request.url.path == "/metrics":
            return await call_next(request)

        method = request.method
        path = _route_path(request)
        start = time.perf_counter()
        status = 500
        try:
            response = await call_next(request)
            status = response.status_code
            return response
        finally:
            duration = time.perf_counter() - start
            HTTP_REQUESTS.labels(method=method, path=path, status=str(status)).inc()
            HTTP_DURATION.labels(method=method, path=path).observe(duration)


def refresh_runtime_gauges(cfg: Settings) -> None:
    try:
        APP_USERS.set(count_users())
    except Exception as exc:
        logger.warning("metrics: users gauge failed: %s", exc)
        APP_USERS.set(-1)

    redis = get_redis()
    APP_REDIS.set(1.0 if redis is not None else 0.0)
    APP_INFO.labels(version="1.0.0", env=cfg.app_env).set(1)


def setup_metrics(app: FastAPI, cfg: Settings) -> None:
    if not cfg.metrics_enabled:
        return

    app.add_middleware(MetricsMiddleware)
    APP_INFO.labels(version="1.0.0", env=cfg.app_env).set(1)

    @app.get("/metrics", include_in_schema=False)
    def metrics_endpoint(request: Request) -> Response:
        if cfg.is_production and cfg.metrics_token:
            auth = request.headers.get("authorization", "")
            expected = f"Bearer {cfg.metrics_token}"
            if auth != expected:
                return Response(status_code=401, content="Unauthorized")

        refresh_runtime_gauges(cfg)
        return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)
