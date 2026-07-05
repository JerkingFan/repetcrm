"""Alembic migration runner with legacy-database stamp support."""

from __future__ import annotations

import logging
from pathlib import Path

from alembic import command
from alembic.config import Config
from alembic.runtime.migration import MigrationContext
from sqlalchemy import inspect

from app.config import settings
from app.database import engine

logger = logging.getLogger(__name__)

_ALEMBIC_INI = Path(__file__).resolve().parent.parent / "alembic.ini"

# Tables introduced after initial Alembic adoption — if missing, run upgrade instead of stamp.
_POST_LEGACY_TABLES = (
    "auth_sessions",
    "lesson_packages",
    "homework_submissions",
    "homework_templates",
    "payment_intents",
    "prompt_templates",
)


def _alembic_config() -> Config:
    cfg = Config(str(_ALEMBIC_INI))
    cfg.set_main_option("sqlalchemy.url", settings.database_url)
    return cfg


def _current_revision() -> str | None:
    with engine.connect() as conn:
        ctx = MigrationContext.configure(conn)
        return ctx.get_current_revision()


def _legacy_database_exists() -> bool:
    return inspect(engine).has_table("users")


def _schema_needs_upgrade() -> bool:
    """True if an old DB is missing tables/columns added in later migrations."""
    insp = inspect(engine)
    for table in _POST_LEGACY_TABLES:
        if not insp.has_table(table):
            return True
    if insp.has_table("students"):
        cols = {c["name"] for c in insp.get_columns("students")}
        if "portal_token" not in cols or "balance" not in cols or "parent_portal_token" not in cols:
            return True
    if insp.has_table("homework_submissions"):
        cols = {c["name"] for c in insp.get_columns("homework_submissions")}
        if "status" not in cols:
            return True
    if insp.has_table("lessons"):
        cols = {c["name"] for c in insp.get_columns("lessons")}
        if "paid_at" not in cols:
            return True
    return False


def run_migrations() -> None:
    """
    Apply Alembic migrations.

    Existing databases created before Alembic (create_all + runtime ALTER) are
    stamped at head only when schema already matches head. Otherwise upgrade runs.
    """
    cfg = _alembic_config()
    current = _current_revision()

    if current is None and _legacy_database_exists():
        if _schema_needs_upgrade():
            logger.warning(
                "Legacy database missing newer schema — running Alembic upgrade (not blind stamp)"
            )
            command.upgrade(cfg, "head")
        else:
            command.stamp(cfg, "head")
            logger.info("Legacy database detected — stamped Alembic head (schema complete)")
        return

    command.upgrade(cfg, "head")
