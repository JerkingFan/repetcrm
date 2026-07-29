"""Fail-fast validation before serving traffic in production."""

from __future__ import annotations

from app.config import Settings

_INSECURE_SECRET_KEYS = frozenset(
    {
        "repetcrm-dev-secret-change-in-production",
        "repetcrm-docker-secret-change-me",
        "repetcrm-local-dev-only-not-for-production-min-32-chars",
        "change-me-in-production",
        "сгенерируйте-длинную-случайную-строку-минимум-32-символа",
    }
)


def validate_production_settings(cfg: Settings) -> None:
    if not cfg.is_production:
        return

    errors: list[str] = []

    key = (cfg.secret_key or "").strip()
    if not key or key in _INSECURE_SECRET_KEYS or len(key) < 32:
        errors.append(
            "SECRET_KEY must be a random string of at least 32 characters "
            "(set APP_ENV=production only after configuring SECRET_KEY)"
        )

    if cfg.cors_allow_localhost_regex:
        errors.append(
            "CORS_ALLOW_LOCALHOST_REGEX must be false in production "
            "(set explicit CORS_ORIGINS instead)"
        )

    if not cfg.cookie_secure:
        errors.append("COOKIE_SECURE must be true in production (HTTPS required)")

    site = cfg.public_site_url.lower()
    if "localhost" in site or "127.0.0.1" in site:
        errors.append(
            "FRONTEND_PUBLIC_URL must be your public site URL (e.g. https://repetcrm.ru) "
            "or set CORS_ORIGINS to that domain — portal/parent links use this"
        )

    # Webhook HMAC is optional until ERIP/acquiring is connected; missing secret blocks
    # /payments/webhook in production via verify_webhook_signature().
    webhook_secret = (cfg.payment_webhook_secret or "").strip()
    if webhook_secret and (
        webhook_secret in _INSECURE_SECRET_KEYS or len(webhook_secret) < 32
    ):
        errors.append(
            "PAYMENT_WEBHOOK_SECRET must be a random string of at least 32 characters "
            "(or remove the line until payment webhooks are enabled)"
        )

    redis_url = (cfg.redis_url or "").strip()
    if not redis_url:
        errors.append(
            "REDIS_URL is required in production (rate limits, job queue, board bus)"
        )

    if cfg.metrics_enabled:
        metrics_token = (cfg.metrics_token or "").strip()
        if not metrics_token or metrics_token in _INSECURE_SECRET_KEYS or len(metrics_token) < 32:
            errors.append(
                "METRICS_TOKEN must be a random string of at least 32 characters "
                "when METRICS_ENABLED=true (protects GET /metrics)"
            )

    if errors:
        raise RuntimeError("Production configuration errors:\n- " + "\n- ".join(errors))


def validate_production_redis_connected(cfg: Settings) -> None:
    """Fail fast if production requires Redis but ping failed."""
    if not cfg.is_production:
        return
    from app.redis_client import get_redis

    if get_redis() is None:
        raise RuntimeError(
            "Redis connection required in production but unavailable "
            "(check REDIS_URL, password, and that the Redis service is running)"
        )
