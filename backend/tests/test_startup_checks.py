from app.config import Settings
from app.startup_checks import validate_production_settings


def test_production_rejects_default_secret():
    cfg = Settings(
        app_env="production",
        secret_key="repetcrm-dev-secret-change-in-production",
        cookie_secure=True,
        cors_allow_localhost_regex=False,
    )
    try:
        validate_production_settings(cfg)
        assert False, "expected RuntimeError"
    except RuntimeError as exc:
        assert "SECRET_KEY" in str(exc)


def test_production_accepts_strong_secret():
    cfg = Settings(
        app_env="production",
        secret_key="x" * 48,
        cookie_secure=True,
        cors_allow_localhost_regex=False,
        payment_webhook_secret="x" * 48,
        frontend_public_url="https://repetcrm.ru",
    )
    validate_production_settings(cfg)


def test_production_accepts_public_url_from_cors():
    cfg = Settings(
        app_env="production",
        secret_key="x" * 48,
        cookie_secure=True,
        cors_allow_localhost_regex=False,
        frontend_public_url="http://localhost:3000",
        cors_origins="https://repetcrm.ru",
    )
    validate_production_settings(cfg)


def test_production_rejects_localhost_public_url():
    cfg = Settings(
        app_env="production",
        secret_key="x" * 48,
        cookie_secure=True,
        cors_allow_localhost_regex=False,
        frontend_public_url="http://localhost:3000",
        cors_origins="http://localhost:3000",
    )
    try:
        validate_production_settings(cfg)
        assert False, "expected RuntimeError"
    except RuntimeError as exc:
        assert "FRONTEND_PUBLIC_URL" in str(exc)


def test_production_allows_missing_webhook_secret():
    """Manual bank-transfer flow works without ERIP webhook secret."""
    cfg = Settings(
        app_env="production",
        secret_key="x" * 48,
        cookie_secure=True,
        cors_allow_localhost_regex=False,
        payment_webhook_secret="",
        frontend_public_url="https://repetcrm.ru",
    )
    validate_production_settings(cfg)


def test_production_rejects_placeholder_webhook_secret():
    cfg = Settings(
        app_env="production",
        secret_key="x" * 48,
        cookie_secure=True,
        cors_allow_localhost_regex=False,
        payment_webhook_secret="change-me-in-production",
    )
    try:
        validate_production_settings(cfg)
        assert False, "expected RuntimeError"
    except RuntimeError as exc:
        assert "PAYMENT_WEBHOOK_SECRET" in str(exc)


def test_development_allows_weak_secret():
    cfg = Settings(app_env="development", secret_key="dev")
    validate_production_settings(cfg)
