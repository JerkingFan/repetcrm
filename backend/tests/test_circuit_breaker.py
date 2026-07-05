"""Circuit breaker unit tests."""

import time

import pytest

from app.services.circuit_breaker import CircuitBreaker, CircuitOpenError


def test_circuit_opens_after_failures():
    cb = CircuitBreaker("test", failure_threshold=2, reset_timeout_sec=30)
    cb.record_failure()
    cb.before_call()
    cb.record_failure()
    with pytest.raises(CircuitOpenError):
        cb.before_call()


def test_circuit_closes_after_reset():
    cb = CircuitBreaker("test", failure_threshold=1, reset_timeout_sec=0.05)
    cb.record_failure()
    with pytest.raises(CircuitOpenError):
        cb.before_call()
    time.sleep(0.2)
    cb.before_call()
    cb.record_success()
    assert cb.allow_request()
