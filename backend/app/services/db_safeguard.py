"""Production safeguards: backup before migrations, block accidental DB switch."""

from __future__ import annotations

import logging
import sqlite3
from pathlib import Path

from app.config import Settings
from app.services.db_startup import backup_sqlite_file, _sqlite_path_from_url, _prune_old_backups

logger = logging.getLogger(__name__)

_BACKEND_DIR = Path(__file__).resolve().parent.parent.parent
_DEFAULT_SQLITE_URL = "sqlite:///./data/repetcrm.db"


def default_sqlite_path() -> Path:
    """Canonical SQLite file path used by Docker volume backend_data."""
    path = _sqlite_path_from_url(_DEFAULT_SQLITE_URL)
    assert path is not None
    return path


def count_sqlite_users_at_path(path: Path) -> int | None:
    """Read user count directly from a SQLite file (no SQLAlchemy)."""
    if not path.is_file():
        return None
    try:
        with sqlite3.connect(str(path)) as conn:
            row = conn.execute("SELECT COUNT(*) FROM users").fetchone()
            return int(row[0]) if row else 0
    except sqlite3.OperationalError:
        return None


def validate_database_switch(cfg: Settings) -> None:
    """
    Refuse to start on PostgreSQL while the default SQLite file still has users,
    unless an explicit migration was completed (SQLITE_MIGRATION_COMPLETED=true).
    """
    url = cfg.database_url
    if url.startswith("sqlite"):
        return

    if "postgres" not in url:
        return

    sqlite_path = default_sqlite_path()
    sqlite_users = count_sqlite_users_at_path(sqlite_path)
    if sqlite_users is None or sqlite_users == 0:
        return

    if cfg.sqlite_migration_completed:
        logger.info(
            "PostgreSQL active; SQLite at %s still has %s user(s) (migration flag set)",
            sqlite_path,
            sqlite_users,
        )
        return

    raise RuntimeError(
        f"Account safety: SQLite file {sqlite_path} contains {sqlite_users} user(s), "
        "but DATABASE_URL points to PostgreSQL. "
        "Your accounts would be invisible (empty Postgres). "
        "Either keep DATABASE_URL=sqlite:///./data/repetcrm.db "
        "or run: python scripts/migrate_sqlite_to_postgres.py "
        "then set SQLITE_MIGRATION_COMPLETED=true in .env.production"
    )


def validate_production_user_floor(cfg: Settings, users_count: int) -> None:
    """Optional fail-fast when user count drops below PRODUCTION_MIN_USERS."""
    if not cfg.is_production:
        return
    minimum = cfg.production_min_users
    if minimum <= 0:
        return
    if users_count < minimum:
        raise RuntimeError(
            f"Account safety: expected at least {minimum} user(s) in database, "
            f"found {users_count}. Check DATABASE_URL and Docker volume backend_data. "
            "Restore from ./data/backups/ if needed."
        )


def backup_default_sqlite(cfg: Settings) -> Path | None:
    """Online backup of the active SQLite DB before Alembic runs."""
    if not cfg.sqlite_backup_on_startup:
        return None
    if not cfg.database_url.startswith("sqlite"):
        return None

    sqlite_path = _sqlite_path_from_url(cfg.database_url)
    if sqlite_path is None or not sqlite_path.is_file():
        return None

    backup_dir = Path(cfg.sqlite_backup_dir)
    if not backup_dir.is_absolute():
        backup_dir = (_BACKEND_DIR / backup_dir).resolve()

    created = backup_sqlite_file(sqlite_path, backup_dir)
    if created:
        _prune_old_backups(backup_dir, cfg.sqlite_backup_keep)
    return created


def run_pre_db_startup(cfg: Settings) -> Path | None:
    """Call before init_db(): validate switch + backup SQLite."""
    validate_database_switch(cfg)
    backup_path = backup_default_sqlite(cfg)
    if backup_path:
        logger.info("Pre-migration SQLite backup: %s", backup_path)
    return backup_path
