"""Optional Sentry error tracking."""

from __future__ import annotations

import logging

from app.config import Settings

logger = logging.getLogger(__name__)


def init_sentry(cfg: Settings) -> None:
    dsn = (cfg.sentry_dsn or "").strip()
    if not dsn:
        return

    try:
        import sentry_sdk
        from sentry_sdk.integrations.fastapi import FastApiIntegration
        from sentry_sdk.integrations.logging import LoggingIntegration
        from sentry_sdk.integrations.starlette import StarletteIntegration
    except ImportError:
        logger.warning("sentry-sdk not installed — skip Sentry")
        return

    sentry_sdk.init(
        dsn=dsn,
        environment=cfg.app_env,
        release=cfg.sentry_release or None,
        traces_sample_rate=cfg.sentry_traces_sample_rate,
        send_default_pii=False,
        integrations=[
            StarletteIntegration(transaction_style="endpoint"),
            FastApiIntegration(transaction_style="endpoint"),
            LoggingIntegration(level=logging.INFO, event_level=logging.ERROR),
        ],
    )
    logger.info("Sentry initialized (env=%s)", cfg.app_env)
