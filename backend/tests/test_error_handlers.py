"""Unified error responses and request ID middleware."""

import uuid

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.exc import SQLAlchemyError

from app.config import Settings
from app.error_handlers import register_exception_handlers
from app.middleware.request_id import RequestIdMiddleware


def _settings(**overrides) -> Settings:
    base = Settings(
        _env_file=None,
        app_env=overrides.pop("app_env", "development"),
    )
    return base.model_copy(update=overrides)


def test_request_id_generated_when_missing(client):
    response = client.get("/health")
    request_id = response.headers.get("X-Request-ID")
    assert request_id
    uuid.UUID(request_id)


def test_request_id_echoed_from_client(client):
    incoming = "test-correlation-id-abc123"
    response = client.get("/health", headers={"X-Request-ID": incoming})
    assert response.headers.get("X-Request-ID") == incoming


def test_validation_error_unified_schema(client):
    response = client.post(
        "/auth/register",
        json={"email": "not-an-email", "password": "x", "name": "Test"},
    )
    assert response.status_code == 422
    body = response.json()
    assert body["code"] == "validation_error"
    assert body["detail"] == "Validation failed"
    assert isinstance(body.get("errors"), list)
    assert body.get("request_id")
    assert response.headers.get("X-Request-ID") == body["request_id"]


def test_production_hides_internal_error(monkeypatch):
    cfg = _settings(app_env="production")

    app = FastAPI()
    app.add_middleware(RequestIdMiddleware)
    register_exception_handlers(app, cfg)

    @app.get("/boom")
    def boom():
        raise RuntimeError("secret database password leaked")

    client = TestClient(app, raise_server_exceptions=False)
    response = client.get("/boom")
    body = response.json()

    assert response.status_code == 500
    assert body["code"] == "internal_error"
    assert body["detail"] == "Internal server error"
    assert "secret" not in str(body)
    assert body.get("request_id")


def test_sqlalchemy_error_schema_in_production():
    cfg = _settings(app_env="production")

    app = FastAPI()
    app.add_middleware(RequestIdMiddleware)
    register_exception_handlers(app, cfg)

    @app.get("/db-fail")
    def db_fail():
        raise SQLAlchemyError("connection refused host=db.internal")

    client = TestClient(app, raise_server_exceptions=False)
    response = client.get("/db-fail")
    body = response.json()

    assert response.status_code == 500
    assert body["code"] == "database_error"
    assert body["detail"] == "Database error"
    assert "connection refused" not in str(body)


def test_pydantic_validation_error_handler():
    app = FastAPI()
    register_exception_handlers(app, _settings())

    @app.get("/validate")
    def validate():
        from pydantic import BaseModel

        class M(BaseModel):
            x: int

        M.model_validate({"x": "nope"})

    client = TestClient(app)
    response = client.get("/validate")
    body = response.json()

    assert response.status_code == 422
    assert body["code"] == "validation_error"
    assert body["errors"]
