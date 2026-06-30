"""SQLite backup and startup database diagnostics."""

from __future__ import annotations

import logging
import re
import shutil
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import SessionLocal
from app.models import User
from app.redis_client import get_redis

logger = logging.getLogger(__name__)

_BACKEND_DIR = Path(__file__).resolve().parent.parent.parent


@dataclass(frozen=True)
class DbStartupReport:
    backend: str
    database_url_redacted: str
    sqlite_path: str | None
    users_count: int
    backup_path: str | None
    warnings: tuple[str, ...]


def _redact_database_url(url: str) -> str:
    return re.sub(r":([^:@/]+)@", ":***@", url)


def _sqlite_path_from_url(url: str) -> Path | None:
    if not url.startswith("sqlite"):
        return None
    # sqlite:///./data/repetcrm.db or sqlite:////absolute/path.db
    raw = url.split("///", 1)[-1] if "///" in url else url.split("://", 1)[-1]
    path = Path(raw)
    if not path.is_absolute():
        path = (_BACKEND_DIR / path).resolve()
    return path


def count_users() -> int:
    db: Session = SessionLocal()
    try:
        return int(db.scalar(select(func.count()).select_from(User)) or 0)
    finally:
        db.close()


def backup_sqlite_file(src: Path, backup_dir: Path) -> Path | None:
    if not src.is_file():
        logger.warning("SQLite backup skipped — file not found: %s", src)
        return None

    backup_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    dst = backup_dir / f"repetcrm_{stamp}.db"

    try:
        with sqlite3.connect(str(src)) as src_conn:
            with sqlite3.connect(str(dst)) as dst_conn:
                src_conn.backup(dst_conn)
        logger.info("SQLite backup created: %s", dst)
        return dst
    except Exception as exc:
        logger.warning("SQLite online backup failed (%s), falling back to copy", exc)
        try:
            shutil.copy2(src, dst)
            logger.info("SQLite backup copied: %s", dst)
            return dst
        except Exception as copy_exc:
            logger.error("SQLite backup failed: %s", copy_exc)
            return None


def _prune_old_backups(backup_dir: Path, keep: int) -> None:
    if keep < 1:
        return
    files = sorted(backup_dir.glob("repetcrm_*.db"), key=lambda p: p.stat().st_mtime, reverse=True)
    for old in files[keep:]:
        try:
            old.unlink()
        except OSError as exc:
            logger.warning("Failed to remove old backup %s: %s", old, exc)


def run_startup_db_checks() -> DbStartupReport:
    cfg = get_settings()
    url = cfg.database_url
    backend = "sqlite" if url.startswith("sqlite") else "postgresql" if "postgres" in url else "other"
    sqlite_path = _sqlite_path_from_url(url) if backend == "sqlite" else None
    users_count = count_users()
    warnings: list[str] = []
    backup_path: str | None = None

    if backend == "sqlite" and sqlite_path and not sqlite_path.is_file() and users_count == 0:
        warnings.append(
            f"SQLite file does not exist yet ({sqlite_path}). "
            "A new database will be created on first write."
        )

    if backend == "sqlite" and sqlite_path and sqlite_path.is_file() and users_count == 0:
        warnings.append(
            f"SQLite file exists ({sqlite_path}) but users table is empty. "
            "Check DATABASE_URL and Docker volume backend_data."
        )

    if backend != "sqlite" and users_count == 0:
        warnings.append(
            "Connected to non-SQLite database with zero users. "
            "If you migrated from SQLite, verify DATABASE_URL points to the correct DB."
        )

    if cfg.sqlite_backup_on_startup and backend == "sqlite" and sqlite_path and sqlite_path.is_file():
        backup_dir = Path(cfg.sqlite_backup_dir)
        if not backup_dir.is_absolute():
            backup_dir = (_BACKEND_DIR / backup_dir).resolve()
        created = backup_sqlite_file(sqlite_path, backup_dir)
        if created:
            backup_path = str(created)
            _prune_old_backups(backup_dir, cfg.sqlite_backup_keep)

    report = DbStartupReport(
        backend=backend,
        database_url_redacted=_redact_database_url(url),
        sqlite_path=str(sqlite_path) if sqlite_path else None,
        users_count=users_count,
        backup_path=backup_path,
        warnings=tuple(warnings),
    )

    logger.info(
        "DB startup: backend=%s users=%s redis=%s url=%s",
        report.backend,
        report.users_count,
        "yes" if get_settings().redis_url.strip() else "no",
        report.database_url_redacted,
    )
    if report.sqlite_path:
        logger.info("DB sqlite path: %s", report.sqlite_path)
    if report.backup_path:
        logger.info("DB backup: %s", report.backup_path)
    for warning in report.warnings:
        logger.warning("DB startup warning: %s", warning)

    return report


def get_db_health() -> dict:
    """Safe subset for /health — no secrets, no emails."""
    cfg = get_settings()
    url = cfg.database_url
    backend = "sqlite" if url.startswith("sqlite") else "postgresql" if "postgres" in url else "other"
    try:
        users_count = count_users()
        db_ok = True
    except Exception:
        users_count = -1
        db_ok = False

    return {
        "backend": backend,
        "ok": db_ok,
        "users_count": users_count,
    }
