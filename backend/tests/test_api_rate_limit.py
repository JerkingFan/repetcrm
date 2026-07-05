"""API rate limit middleware."""

import importlib

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.middleware.api_rate_limit import ApiRateLimitMiddleware


def test_api_rate_limit_returns_429(monkeypatch):
    monkeypatch.setenv("API_RATE_LIMIT_ENABLED", "true")
    monkeypatch.setenv("API_RATE_LIMIT_MAX", "3")
    monkeypatch.setenv("API_RATE_LIMIT_WINDOW_SEC", "60")

    import app.config as config_module
    import app.middleware.api_rate_limit as rate_limit_module

    rate_limit_module._limiter = None
    importlib.reload(config_module)

    app = FastAPI()

    @app.get("/ping")
    def ping():
        return {"ok": True}

    app.add_middleware(ApiRateLimitMiddleware)
    client = TestClient(app)

    assert client.get("/ping").status_code == 200
    assert client.get("/ping").status_code == 200
    assert client.get("/ping").status_code == 200
    blocked = client.get("/ping")
    assert blocked.status_code == 429
    assert blocked.headers.get("retry-after")


def test_health_skips_rate_limit(monkeypatch, tmp_path):
    monkeypatch.setenv("MEDIA_DIR", str(tmp_path / "media"))
    (tmp_path / "media").mkdir()
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.setenv("API_RATE_LIMIT_ENABLED", "true")
    monkeypatch.setenv("API_RATE_LIMIT_MAX", "1")
    monkeypatch.setenv("API_RATE_LIMIT_WINDOW_SEC", "60")

    import app.config as config_module
    import app.main as main_module
    import app.middleware.api_rate_limit as rate_limit_module

    rate_limit_module._limiter = None
    importlib.reload(config_module)
    importlib.reload(main_module)

    client = TestClient(main_module.app)
    for _ in range(5):
        assert client.get("/health").status_code == 200
