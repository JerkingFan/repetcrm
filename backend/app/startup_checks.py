"""Fail-fast validation before serving traffic in production."""

from __future__ import annotations

from app.config import Settings

_INSECURE_SECRET_KEYS = frozenset(
    {
        "repetcrm-dev-secret-change-in-production",
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

    if errors:
        raise RuntimeError("Production configuration errors:\n- " + "\n- ".join(errors))
