"""Shared Redis connection (sync). Falls back gracefully when Redis is unavailable."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from app.config import get_settings

if TYPE_CHECKING:
    from redis import Redis

logger = logging.getLogger(__name__)

_redis: Redis | None = None
_redis_checked = False


def get_redis() -> Redis | None:
    """Return a Redis client or None if disabled/unavailable."""
    global _redis, _redis_checked
    if _redis_checked:
        return _redis

    _redis_checked = True
    url = get_settings().redis_url.strip()
    if not url:
        logger.info("REDIS_URL not set — using in-memory fallbacks for cache/rate limits")
        return None

    try:
        import redis

        client: Redis = redis.from_url(
            url,
            decode_responses=True,
            socket_connect_timeout=2,
            socket_timeout=2,
            health_check_interval=30,
        )
        client.ping()
        _redis = client
        logger.info("Redis connected")
    except Exception as exc:
        logger.warning("Redis unavailable (%s) — using in-memory fallbacks", exc)
        _redis = None
    return _redis


def close_redis() -> None:
    global _redis, _redis_checked
    if _redis is not None:
        try:
            _redis.close()
        except Exception:
            pass
    _redis = None
    _redis_checked = False
