"""Alembic migration runner with legacy-database stamp support."""

from __future__ import annotations

import logging
from pathlib import Path

from alembic import command
from alembic.config import Config
from alembic.runtime.migration import MigrationContext
from sqlalchemy import inspect
from sqlalchemy.engine import Inspector

from app.config import settings
from app.database import engine

logger = logging.getLogger(__name__)

_ALEMBIC_INI = Path(__file__).resolve().parent.parent / "alembic.ini"
_HEAD_REVISION = "f3a4b5c6d7e8"


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


def _detect_legacy_revision(insp: Inspector) -> str:
    """Best-effort Alembic revision for a populated DB without alembic_version."""
    if insp.has_table("payment_receipts"):
        return _HEAD_REVISION

    if insp.has_table("users"):
        user_cols = {c["name"] for c in insp.get_columns("users")}
        if "booking_slug" in user_cols or insp.has_table("trial_bookings"):
            return "e2f3a4b5c6d7"

    if insp.has_table("homework_submissions"):
        hs_cols = {c["name"] for c in insp.get_columns("homework_submissions")}
        if "status" in hs_cols:
            return "d1e2f3a4b5c6"

    if insp.has_table("students"):
        st_cols = {c["name"] for c in insp.get_columns("students")}
        if "parent_portal_token" in st_cols:
            return "c0d1e2f3a4b5"

    if insp.has_table("payment_intents") or insp.has_table("prompt_templates"):
        return "b9c0d1e2f3a4"

    if insp.has_table("homework_templates"):
        return "a8b9c0d1e2f3"

    if insp.has_table("students"):
        st_cols = {c["name"] for c in insp.get_columns("students")}
        if "portal_token" in st_cols or "balance" in st_cols or insp.has_table("lesson_packages"):
            return "f7a8b9c0d1e2"

    if insp.has_table("auth_sessions"):
        return "e6f7a8b9c0d1"

    if insp.has_table("board_snapshots"):
        return "d5e6f7a8b9c0"

    return "dfa02a76bcc0"


def run_migrations() -> None:
    """
    Apply Alembic migrations.

    Existing databases created before Alembic (create_all + runtime ALTER) are
    stamped at the detected revision, then upgraded to head — never replayed from
    initial_schema when users already exist.
    """
    cfg = _alembic_config()
    current = _current_revision()

    if current is None and _legacy_database_exists():
        stamp_rev = _detect_legacy_revision(inspect(engine))
        if stamp_rev == _HEAD_REVISION:
            command.stamp(cfg, "head")
            logger.info("Legacy database — schema at head, stamped %s", _HEAD_REVISION)
        else:
            logger.warning(
                "Legacy database without alembic_version — stamping %s then upgrading to head",
                stamp_rev,
            )
            command.stamp(cfg, stamp_rev)
            command.upgrade(cfg, "head")
        return

    command.upgrade(cfg, "head")
