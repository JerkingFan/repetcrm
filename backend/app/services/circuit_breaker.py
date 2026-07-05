"""Simple circuit breaker for external HTTP dependencies."""

from __future__ import annotations

import logging
import threading
import time

logger = logging.getLogger(__name__)


class CircuitOpenError(Exception):
    """Raised when the circuit is open and calls are rejected."""


class CircuitBreaker:
    def __init__(self, name: str, *, failure_threshold: int = 3, reset_timeout_sec: float = 60.0):
        self.name = name
        self.failure_threshold = max(1, failure_threshold)
        self.reset_timeout_sec = max(0.05, reset_timeout_sec)
        self._lock = threading.Lock()
        self._failures = 0
        self._opened_at: float | None = None

    def _is_open(self, now: float) -> bool:
        if self._opened_at is None:
            return False
        if now - self._opened_at >= self.reset_timeout_sec:
            self._failures = 0
            self._opened_at = None
            return False
        return True

    def before_call(self) -> None:
        with self._lock:
            now = time.monotonic()
            if self._opened_at is not None:
                if now - self._opened_at < self.reset_timeout_sec:
                    raise CircuitOpenError(f"{self.name} circuit open")
                self._opened_at = None
                self._failures = 0

    def record_success(self) -> None:
        with self._lock:
            self._failures = 0
            self._opened_at = None

    def record_failure(self) -> None:
        with self._lock:
            self._failures += 1
            if self._failures >= self.failure_threshold:
                if self._opened_at is None:
                    logger.warning("%s circuit opened after %s failures", self.name, self._failures)
                self._opened_at = time.monotonic()

    def allow_request(self) -> bool:
        with self._lock:
            return not self._is_open(time.monotonic())
