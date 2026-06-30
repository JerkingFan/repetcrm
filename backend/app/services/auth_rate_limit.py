"""Rate limits for auth endpoints — Redis sliding window with in-memory fallback."""

from __future__ import annotations

import hashlib
import logging
import threading
import time
from collections import defaultdict

from app.redis_client import get_redis

logger = logging.getLogger(__name__)


def redact_email(email: str) -> str:
    local, _, domain = email.strip().partition("@")
    if not domain:
        return "***"
    if len(local) <= 1:
        return f"*@{domain}"
    return f"{local[0]}***@{domain}"


def email_fingerprint(email: str) -> str:
    normalized = email.strip().lower()
    return hashlib.sha256(normalized.encode()).hexdigest()[:12]


class SlidingWindowLimiter:
    """In-memory fallback when Redis is unavailable."""

    def __init__(self, max_events: int, window_sec: int, *, prefix: str = "mem"):
        self.max_events = max_events
        self.window_sec = window_sec
        self.prefix = prefix
        self._lock = threading.Lock()
        self._events: dict[str, list[float]] = defaultdict(list)

    def _full_key(self, key: str) -> str:
        return f"{self.prefix}:{key}"

    def _prune(self, key: str, now: float) -> list[float]:
        cutoff = now - self.window_sec
        kept = [t for t in self._events[key] if t > cutoff]
        self._events[key] = kept
        return kept

    def is_blocked(self, key: str) -> bool:
        with self._lock:
            now = time.monotonic()
            return len(self._prune(key, now)) >= self.max_events

    def record(self, key: str) -> int:
        with self._lock:
            now = time.monotonic()
            events = self._prune(key, now)
            events.append(now)
            self._events[key] = events
            return len(events)

    def clear(self, key: str) -> None:
        with self._lock:
            self._events.pop(key, None)

    def retry_after_sec(self, key: str) -> int:
        with self._lock:
            now = time.monotonic()
            events = self._prune(key, now)
            if len(events) < self.max_events:
                return 0
            oldest = min(events)
            return max(1, int(self.window_sec - (now - oldest)) + 1)


class RedisSlidingWindowLimiter:
    """Atomic sliding window via sorted set (works across workers/instances)."""

    def __init__(self, max_events: int, window_sec: int, *, prefix: str):
        self.max_events = max_events
        self.window_sec = window_sec
        self.prefix = prefix
        self._fallback = SlidingWindowLimiter(max_events, window_sec, prefix=f"fb:{prefix}")

    def _redis_key(self, key: str) -> str:
        return f"ratelimit:{self.prefix}:{key}"

    def _use_redis(self):
        return get_redis()

    def is_blocked(self, key: str) -> bool:
        redis = self._use_redis()
        if redis is None:
            return self._fallback.is_blocked(key)

        now = time.time()
        rkey = self._redis_key(key)
        try:
            pipe = redis.pipeline()
            pipe.zremrangebyscore(rkey, 0, now - self.window_sec)
            pipe.zcard(rkey)
            _, count = pipe.execute()
            return int(count) >= self.max_events
        except Exception as exc:
            logger.warning("redis rate limit is_blocked failed: %s", exc)
            return self._fallback.is_blocked(key)

    def record(self, key: str) -> int:
        redis = self._use_redis()
        if redis is None:
            return self._fallback.record(key)

        now = time.time()
        rkey = self._redis_key(key)
        member = f"{now:.6f}:{time.monotonic_ns()}"
        try:
            pipe = redis.pipeline()
            pipe.zremrangebyscore(rkey, 0, now - self.window_sec)
            pipe.zadd(rkey, {member: now})
            pipe.zcard(rkey)
            pipe.expire(rkey, self.window_sec + 1)
            _, _, count, _ = pipe.execute()
            return int(count)
        except Exception as exc:
            logger.warning("redis rate limit record failed: %s", exc)
            return self._fallback.record(key)

    def clear(self, key: str) -> None:
        redis = self._use_redis()
        if redis is not None:
            try:
                redis.delete(self._redis_key(key))
            except Exception:
                pass
        self._fallback.clear(key)

    def retry_after_sec(self, key: str) -> int:
        redis = self._use_redis()
        if redis is None:
            return self._fallback.retry_after_sec(key)

        now = time.time()
        rkey = self._redis_key(key)
        try:
            redis.zremrangebyscore(rkey, 0, now - self.window_sec)
            oldest = redis.zrange(rkey, 0, 0, withscores=True)
            count = redis.zcard(rkey)
            if int(count) < self.max_events or not oldest:
                return 0
            oldest_ts = float(oldest[0][1])
            return max(1, int(self.window_sec - (now - oldest_ts)) + 1)
        except Exception as exc:
            logger.warning("redis rate limit retry_after failed: %s", exc)
            return self._fallback.retry_after_sec(key)


_login_limiter: RedisSlidingWindowLimiter | None = None
_register_limiter: RedisSlidingWindowLimiter | None = None


def get_login_limiter(max_failures: int, window_sec: int) -> RedisSlidingWindowLimiter:
    global _login_limiter
    if _login_limiter is None:
        _login_limiter = RedisSlidingWindowLimiter(
            max_failures, window_sec, prefix="auth:login"
        )
    return _login_limiter


def get_register_limiter(max_events: int, window_sec: int) -> RedisSlidingWindowLimiter:
    global _register_limiter
    if _register_limiter is None:
        _register_limiter = RedisSlidingWindowLimiter(
            max_events, window_sec, prefix="auth:register"
        )
    return _register_limiter
