"""Dashboard stats cache (Redis with in-memory fallback)."""

from __future__ import annotations

import json
import logging
import threading
import time
from typing import Any

from app.config import get_settings
from app.redis_client import get_redis

logger = logging.getLogger(__name__)

_PREFIX = "dash:v1:user:"

_mem_lock = threading.Lock()
_mem_cache: dict[str, tuple[float, dict[str, Any]]] = {}


def _cache_key(tutor_id: int) -> str:
    return f"{_PREFIX}{tutor_id}"


def get_cached_dashboard(tutor_id: int) -> dict[str, Any] | None:
    key = _cache_key(tutor_id)
    redis = get_redis()
    if redis is not None:
        try:
            raw = redis.get(key)
            if raw:
                return json.loads(raw)
        except Exception as exc:
            logger.warning("dashboard cache read failed tutor=%s: %s", tutor_id, exc)

    with _mem_lock:
        entry = _mem_cache.get(key)
        if entry and entry[0] > time.monotonic():
            return entry[1]
    return None


def set_cached_dashboard(tutor_id: int, stats: dict[str, Any]) -> None:
    key = _cache_key(tutor_id)
    ttl = get_settings().dashboard_cache_ttl_sec
    payload = json.dumps(stats, ensure_ascii=False)

    redis = get_redis()
    if redis is not None:
        try:
            redis.setex(key, ttl, payload)
            return
        except Exception as exc:
            logger.warning("dashboard cache write failed tutor=%s: %s", tutor_id, exc)

    with _mem_lock:
        _mem_cache[key] = (time.monotonic() + ttl, stats)


def invalidate_dashboard(tutor_id: int) -> None:
    key = _cache_key(tutor_id)
    redis = get_redis()
    if redis is not None:
        try:
            redis.delete(key)
        except Exception as exc:
            logger.warning("dashboard cache invalidate failed tutor=%s: %s", tutor_id, exc)

    with _mem_lock:
        _mem_cache.pop(key, None)
