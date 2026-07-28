"""Alembic migration runner with legacy-database stamp support."""

from __future__ import annotations

import logging
from pathlib import Path

from alembic import command
from alembic.config import Config
from alembic.runtime.migration import MigrationContext
import sqlalchemy as sa
from sqlalchemy import inspect, text
from sqlalchemy.engine import Inspector
from sqlalchemy.schema import Column

from app.config import settings
from app.database import engine

logger = logging.getLogger(__name__)

_ALEMBIC_INI = Path(__file__).resolve().parent.parent / "alembic.ini"
_HEAD_REVISION = "c3d4e5f6a7b8"


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


def _repair_missing_auth_sessions() -> None:
    """Old DBs may have users but no auth_sessions — login would 500 on session insert."""
    insp = inspect(engine)
    if not insp.has_table("users") or insp.has_table("auth_sessions"):
        return

    logger.warning("Legacy DB repair: creating missing auth_sessions table")
    dialect = engine.dialect.name
    with engine.begin() as conn:
        if dialect == "sqlite":
            conn.execute(
                text(
                    """
                    CREATE TABLE auth_sessions (
                        id INTEGER NOT NULL PRIMARY KEY,
                        user_id INTEGER NOT NULL,
                        token_hash VARCHAR(64) NOT NULL,
                        expires_at DATETIME NOT NULL,
                        revoked_at DATETIME,
                        created_at DATETIME NOT NULL DEFAULT (CURRENT_TIMESTAMP),
                        last_ip VARCHAR(45) NOT NULL DEFAULT '',
                        user_agent VARCHAR(512) NOT NULL DEFAULT '',
                        FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE
                    )
                    """
                )
            )
            conn.execute(
                text(
                    "CREATE UNIQUE INDEX IF NOT EXISTS ix_auth_sessions_token_hash "
                    "ON auth_sessions (token_hash)"
                )
            )
            conn.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS ix_auth_sessions_user_id "
                    "ON auth_sessions (user_id)"
                )
            )
        else:
            conn.execute(
                text(
                    """
                    CREATE TABLE IF NOT EXISTS auth_sessions (
                        id SERIAL PRIMARY KEY,
                        user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                        token_hash VARCHAR(64) NOT NULL UNIQUE,
                        expires_at TIMESTAMP NOT NULL,
                        revoked_at TIMESTAMP,
                        created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                        last_ip VARCHAR(45) NOT NULL DEFAULT '',
                        user_agent VARCHAR(512) NOT NULL DEFAULT ''
                    )
                    """
                )
            )
            conn.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS ix_auth_sessions_user_id "
                    "ON auth_sessions (user_id)"
                )
            )
    logger.info("auth_sessions table created")


# Columns on users added after early deployments (Alembic stamp may skip DDL).
_USER_SQLITE_COLUMN_DDLS: dict[str, str] = {
    "telegram_chat_id": "VARCHAR(64) NOT NULL DEFAULT ''",
    "notify_email": "BOOLEAN NOT NULL DEFAULT 1",
    "notify_telegram": "BOOLEAN NOT NULL DEFAULT 0",
    "notify_lesson_tomorrow": "BOOLEAN NOT NULL DEFAULT 1",
    "notify_unpaid": "BOOLEAN NOT NULL DEFAULT 1",
    "notify_homework_ready": "BOOLEAN NOT NULL DEFAULT 1",
    "booking_slug": "VARCHAR(64)",
    "booking_enabled": "BOOLEAN NOT NULL DEFAULT 0",
    "booking_hours": "TEXT NOT NULL DEFAULT '[]'",
    "booking_reply_text": "TEXT NOT NULL DEFAULT ''",
    "payment_details": "TEXT NOT NULL DEFAULT ''",
}


def _add_missing_columns(table: str, column_ddls: dict[str, str]) -> None:
    insp = inspect(engine)
    if not insp.has_table(table):
        return

    existing = {c["name"] for c in insp.get_columns(table)}
    dialect = engine.dialect.name
    added: list[str] = []

    with engine.begin() as conn:
        for col, ddl in column_ddls.items():
            if col in existing:
                continue
            if dialect == "sqlite":
                conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {col} {ddl}"))
            else:
                conn.execute(text(f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS {col} {ddl}"))
            added.append(col)

    if added:
        logger.warning("Legacy DB repair: added %s columns: %s", table, ", ".join(added))


def _repair_users_table_columns() -> None:
    _add_missing_columns("users", _USER_SQLITE_COLUMN_DDLS)


_STUDENTS_SQLITE_COLUMN_DDLS: dict[str, str] = {
    "portal_token": "VARCHAR(64)",
    "balance": "FLOAT NOT NULL DEFAULT 0",
    "first_lesson_at": "DATE",
    "last_lesson_at": "DATE",
    "student_status": "VARCHAR(20) NOT NULL DEFAULT 'active'",
    "parent_name": "VARCHAR(255) NOT NULL DEFAULT ''",
    "parent_email": "VARCHAR(255) NOT NULL DEFAULT ''",
    "parent_phone": "VARCHAR(64) NOT NULL DEFAULT ''",
    "parent_notify_email": "BOOLEAN NOT NULL DEFAULT 1",
    "parent_portal_token": "VARCHAR(64)",
    "portal_nickname": "VARCHAR(64) NOT NULL DEFAULT ''",
    "portal_theme": "VARCHAR(32) NOT NULL DEFAULT 'ocean'",
    "portal_avatar": "VARCHAR(32) NOT NULL DEFAULT 'rocket'",
}

_LESSONS_SQLITE_COLUMN_DDLS: dict[str, str] = {
    "paid_at": "DATETIME",
    "payment_source": "VARCHAR(30)",
    "series_id": "INTEGER",
    "package_id": "INTEGER",
}

_BOARDS_SQLITE_COLUMN_DDLS: dict[str, str] = {
    "share_writable": "BOOLEAN NOT NULL DEFAULT 1",
}


def _repair_missing_payment_receipts() -> None:
    insp = inspect(engine)
    if insp.has_table("payment_receipts") or not insp.has_table("students"):
        return

    logger.warning("Legacy DB repair: creating payment_receipts table")
    dialect = engine.dialect.name
    with engine.begin() as conn:
        if dialect == "sqlite":
            conn.execute(
                text(
                    """
                    CREATE TABLE payment_receipts (
                        id INTEGER NOT NULL PRIMARY KEY,
                        tutor_id INTEGER NOT NULL,
                        student_id INTEGER NOT NULL,
                        amount FLOAT NOT NULL,
                        status VARCHAR(20) NOT NULL DEFAULT 'pending',
                        file_path VARCHAR(512) NOT NULL DEFAULT '',
                        original_filename VARCHAR(255) NOT NULL DEFAULT '',
                        mime_type VARCHAR(80) NOT NULL DEFAULT '',
                        parent_note TEXT NOT NULL DEFAULT '',
                        tutor_note TEXT NOT NULL DEFAULT '',
                        created_at DATETIME NOT NULL DEFAULT (CURRENT_TIMESTAMP),
                        reviewed_at DATETIME,
                        FOREIGN KEY(student_id) REFERENCES students (id) ON DELETE CASCADE,
                        FOREIGN KEY(tutor_id) REFERENCES users (id) ON DELETE CASCADE
                    )
                    """
                )
            )
            conn.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS ix_payment_receipts_tutor_id "
                    "ON payment_receipts (tutor_id)"
                )
            )
            conn.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS ix_payment_receipts_student_id "
                    "ON payment_receipts (student_id)"
                )
            )
            conn.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS ix_payment_receipts_status "
                    "ON payment_receipts (status)"
                )
            )
        else:
            conn.execute(
                text(
                    """
                    CREATE TABLE IF NOT EXISTS payment_receipts (
                        id SERIAL PRIMARY KEY,
                        tutor_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                        student_id INTEGER NOT NULL REFERENCES students(id) ON DELETE CASCADE,
                        amount DOUBLE PRECISION NOT NULL,
                        status VARCHAR(20) NOT NULL DEFAULT 'pending',
                        file_path VARCHAR(512) NOT NULL DEFAULT '',
                        original_filename VARCHAR(255) NOT NULL DEFAULT '',
                        mime_type VARCHAR(80) NOT NULL DEFAULT '',
                        parent_note TEXT NOT NULL DEFAULT '',
                        tutor_note TEXT NOT NULL DEFAULT '',
                        created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                        reviewed_at TIMESTAMP
                    )
                    """
                )
            )
            conn.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS ix_payment_receipts_tutor_id "
                    "ON payment_receipts (tutor_id)"
                )
            )
            conn.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS ix_payment_receipts_student_id "
                    "ON payment_receipts (student_id)"
                )
            )
            conn.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS ix_payment_receipts_status "
                    "ON payment_receipts (status)"
                )
            )
    logger.info("payment_receipts table created")


def _repair_missing_board_snapshots() -> None:
    insp = inspect(engine)
    if insp.has_table("board_snapshots") or not insp.has_table("boards"):
        return

    logger.warning("Legacy DB repair: creating board_snapshots table")
    dialect = engine.dialect.name
    with engine.begin() as conn:
        if dialect == "sqlite":
            conn.execute(
                text(
                    """
                    CREATE TABLE board_snapshots (
                        id INTEGER NOT NULL PRIMARY KEY,
                        board_id INTEGER NOT NULL,
                        state_json TEXT NOT NULL DEFAULT '{}',
                        created_at DATETIME NOT NULL DEFAULT (CURRENT_TIMESTAMP),
                        FOREIGN KEY(board_id) REFERENCES boards (id) ON DELETE CASCADE
                    )
                    """
                )
            )
            conn.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS ix_board_snapshots_board_id "
                    "ON board_snapshots (board_id)"
                )
            )
            conn.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS ix_board_snapshots_created_at "
                    "ON board_snapshots (created_at)"
                )
            )
        else:
            conn.execute(
                text(
                    """
                    CREATE TABLE IF NOT EXISTS board_snapshots (
                        id SERIAL PRIMARY KEY,
                        board_id INTEGER NOT NULL REFERENCES boards(id) ON DELETE CASCADE,
                        state_json TEXT NOT NULL DEFAULT '{}',
                        created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
                    )
                    """
                )
            )
            conn.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS ix_board_snapshots_board_id "
                    "ON board_snapshots (board_id)"
                )
            )
            conn.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS ix_board_snapshots_created_at "
                    "ON board_snapshots (created_at)"
                )
            )
    logger.info("board_snapshots table created")


def _sqlite_type_for_column(col: Column) -> str:
    t = col.type
    if isinstance(t, sa.Integer):
        return "INTEGER"
    if isinstance(t, sa.String):
        return f"VARCHAR({t.length or 255})"
    if isinstance(t, sa.Text):
        return "TEXT"
    if isinstance(t, sa.Boolean):
        return "BOOLEAN"
    if isinstance(t, sa.Float):
        return "FLOAT"
    if isinstance(t, sa.DateTime):
        return "DATETIME"
    if isinstance(t, sa.Date):
        return "DATE"
    return str(t.compile(dialect=engine.dialect))


def _default_sql_for_column(col: Column, dialect: str) -> str | None:
    if col.server_default is not None:
        arg = col.server_default.arg
        if isinstance(arg, sa.TextClause):
            return arg.text
    default = col.default
    if default is not None and getattr(default, "is_scalar", False):
        val = default.arg
        if isinstance(val, bool):
            if dialect == "sqlite":
                return "1" if val else "0"
            return "true" if val else "false"
        if isinstance(val, (int, float)):
            return str(val)
        if isinstance(val, str):
            escaped = val.replace("'", "''")
            return f"'{escaped}'"
    return None


def _column_add_ddl(col: Column, dialect: str) -> str:
    sql_type = _sqlite_type_for_column(col) if dialect == "sqlite" else str(
        col.type.compile(dialect=engine.dialect)
    )
    parts = [sql_type]
    default_sql = _default_sql_for_column(col, dialect)
    if default_sql:
        parts.append(f"DEFAULT {default_sql}")
    if col.nullable is False:
        parts.append("NOT NULL")
    return " ".join(parts)


def _repair_missing_tables_from_models() -> None:
    """Create any ORM tables missing from legacy DBs (e.g. board_snapshots)."""
    from app.database import Base

    import app.models  # noqa: F401

    insp = inspect(engine)
    missing = [t.name for t in Base.metadata.sorted_tables if not insp.has_table(t.name)]
    if not missing:
        return
    Base.metadata.create_all(bind=engine, checkfirst=True)
    logger.warning("Legacy DB repair: created tables: %s", ", ".join(sorted(missing)))


def _repair_orm_missing_columns() -> None:
    """Add columns present in SQLAlchemy models but missing in the live schema."""
    from app.database import Base

    import app.models  # noqa: F401

    dialect = engine.dialect.name
    if dialect not in ("sqlite", "postgresql"):
        return

    insp = inspect(engine)
    for table in Base.metadata.sorted_tables:
        if not insp.has_table(table.name):
            continue
        existing = {c["name"] for c in insp.get_columns(table.name)}
        added: list[str] = []
        with engine.begin() as conn:
            for col in table.columns:
                if col.name in existing:
                    continue
                ddl = _column_add_ddl(col, dialect)
                if dialect == "sqlite":
                    stmt = f"ALTER TABLE {table.name} ADD COLUMN {col.name} {ddl}"
                else:
                    stmt = (
                        f"ALTER TABLE {table.name} ADD COLUMN IF NOT EXISTS "
                        f"{col.name} {ddl}"
                    )
                try:
                    conn.execute(text(stmt))
                    added.append(col.name)
                except Exception as exc:
                    logger.warning(
                        "Legacy DB repair: failed %s.%s: %s",
                        table.name,
                        col.name,
                        exc,
                    )
        if added:
            logger.warning(
                "Legacy DB repair: added %s columns: %s",
                table.name,
                ", ".join(added),
            )


def repair_legacy_schema() -> None:
    """Idempotent fixes for DBs stamped ahead of their real schema."""
    _repair_missing_tables_from_models()
    _repair_orm_missing_columns()
    _repair_missing_auth_sessions()
    _add_missing_columns("users", _USER_SQLITE_COLUMN_DDLS)
    _add_missing_columns("students", _STUDENTS_SQLITE_COLUMN_DDLS)
    _add_missing_columns("lessons", _LESSONS_SQLITE_COLUMN_DDLS)
    _add_missing_columns("boards", _BOARDS_SQLITE_COLUMN_DDLS)
    _repair_missing_payment_receipts()
    _repair_missing_board_snapshots()


def _detect_legacy_revision(insp: Inspector) -> str:
    """Best-effort Alembic revision for a populated DB without alembic_version."""
    if insp.has_table("student_daily_challenges"):
        return "c3d4e5f6a7b8"

    if insp.has_table("lesson_reschedule_requests"):
        return "b2c3d4e5f6a7"

    if insp.has_table("users"):
        user_cols = {c["name"] for c in insp.get_columns("users")}
        if "booking_slug" in user_cols or insp.has_table("trial_bookings"):
            return "e2f3a4b5c6d7"

    if insp.has_table("payment_receipts"):
        return "f3a4b5c6d7e8"

    if insp.has_table("homework_submissions"):
        hs_cols = {c["name"] for c in insp.get_columns("homework_submissions")}
        if "ai_review_status" in hs_cols:
            return "a1b2c3d4e5f6"
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

    if insp.has_table("board_snapshots"):
        return "d5e6f7a8b9c0"

    if insp.has_table("auth_sessions"):
        return "dfa02a76bcc0"

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
        repair_legacy_schema()
        return

    command.upgrade(cfg, "head")
    if _legacy_database_exists():
        repair_legacy_schema()
