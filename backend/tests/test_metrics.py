"""Prometheus /metrics endpoint tests."""

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.metrics import setup_metrics


def test_metrics_endpoint_returns_prometheus_format():
    class DevCfg:
        metrics_enabled = True
        is_production = False
        metrics_token = ""
        app_env = "development"

    app = FastAPI()
    setup_metrics(app, DevCfg())  # type: ignore[arg-type]
    client = TestClient(app)
    response = client.get("/metrics")
    assert response.status_code == 200
    assert "text/plain" in response.headers.get("content-type", "")
    body = response.text
    assert "http_requests_total" in body
    assert "repetcrm_users_total" in body


def test_metrics_requires_token_in_production():
    class ProdCfg:
        metrics_enabled = True
        is_production = True
        metrics_token = "secret-metrics-token"
        app_env = "production"

    app = FastAPI()
    setup_metrics(app, ProdCfg())  # type: ignore[arg-type]
    client = TestClient(app)

    assert client.get("/metrics").status_code == 401
    assert (
        client.get(
            "/metrics",
            headers={"Authorization": "Bearer secret-metrics-token"},
        ).status_code
        == 200
    )
