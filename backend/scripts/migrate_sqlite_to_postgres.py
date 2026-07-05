#!/usr/bin/env python3
"""
Copy all RepetCRM data from SQLite to PostgreSQL without losing accounts.

Usage (from backend/):
  export DATABASE_URL=postgresql+psycopg2://user:pass@host:5432/repetcrm
  python scripts/migrate_sqlite_to_postgres.py --sqlite ./data/repetcrm.db

Dry run (counts only):
  python scripts/migrate_sqlite_to_postgres.py --sqlite ./data/repetcrm.db --dry-run
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import Engine

_BACKEND = Path(__file__).resolve().parent.parent
if str(_BACKEND) not in sys.path:
    sys.path.insert(0, str(_BACKEND))

# Table order respects foreign keys; IDs are preserved.
_TABLES = (
    "users",
    "boards",
    "auth_sessions",
    "students",
    "lessons",
    "checklist_items",
    "homeworks",
)


def _row_count(engine: Engine, table: str) -> int:
    with engine.connect() as conn:
        return int(conn.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar_one())


def _copy_table(src: Engine, dst: Engine, table: str) -> int:
    with src.connect() as sconn:
        rows = sconn.execute(text(f"SELECT * FROM {table}")).mappings().all()
    if not rows:
        return 0

    columns = list(rows[0].keys())
    col_list = ", ".join(columns)
    placeholders = ", ".join(f":{c}" for c in columns)
    insert_sql = text(f"INSERT INTO {table} ({col_list}) VALUES ({placeholders})")

    with dst.begin() as dconn:
        for row in rows:
            dconn.execute(insert_sql, dict(row))
    return len(rows)


def _reset_sequences(dst: Engine) -> None:
    """Align PostgreSQL serial sequences with max(id) after explicit ID inserts."""
    if "postgres" not in str(dst.url):
        return
    insp = inspect(dst)
    with dst.begin() as conn:
        for table in _TABLES:
            if not insp.has_table(table):
                continue
            pk_cols = insp.get_pk_constraint(table).get("constrained_columns") or []
            if pk_cols != ["id"]:
                continue
            conn.execute(
                text(
                    f"SELECT setval(pg_get_serial_sequence('{table}', 'id'), "
                    f"COALESCE((SELECT MAX(id) FROM {table}), 1), true)"
                )
            )


def _run_alembic_on_target(postgres_url: str) -> None:
    from alembic import command
    from alembic.config import Config

    ini = _BACKEND / "alembic.ini"
    cfg = Config(str(ini))
    cfg.set_main_option("sqlalchemy.url", postgres_url)
    command.upgrade(cfg, "head")


def migrate(sqlite_path: Path, postgres_url: str, *, dry_run: bool = False) -> None:
    if not sqlite_path.is_file():
        raise SystemExit(f"SQLite file not found: {sqlite_path}")

    src = create_engine(f"sqlite:///{sqlite_path.as_posix()}")
    dst = create_engine(postgres_url)

    src_users = _row_count(src, "users")
    print(f"Source SQLite: {sqlite_path} — {src_users} user(s)")

    if dry_run:
        for table in _TABLES:
            print(f"  {table}: {_row_count(src, table)} row(s)")
        print("Dry run complete — no changes written.")
        return

    dst_users_before = 0
    if inspect(dst).has_table("users"):
        dst_users_before = _row_count(dst, "users")
    if dst_users_before > 0:
        raise SystemExit(
            f"Target PostgreSQL already has {dst_users_before} user(s). "
            "Use an empty database or drop tables first."
        )

    print("Applying Alembic schema on PostgreSQL...")
    _run_alembic_on_target(postgres_url)

    print("Copying data...")
    for table in _TABLES:
        n = _copy_table(src, dst, table)
        print(f"  {table}: {n} row(s)")

    _reset_sequences(dst)

    dst_users = _row_count(dst, "users")
    if dst_users != src_users:
        raise SystemExit(
            f"Verification failed: SQLite had {src_users} users, PostgreSQL has {dst_users}"
        )

    print(f"Done. {dst_users} user account(s) migrated successfully.")
    print("Next steps:")
    print("  1. Set DATABASE_URL to the PostgreSQL URL in .env.production")
    print("  2. Set SQLITE_MIGRATION_COMPLETED=true")
    print("  3. docker compose ... --profile postgres up -d --build")
    print("  4. curl /health — database.users_count must match", dst_users)


def main() -> None:
    parser = argparse.ArgumentParser(description="Migrate RepetCRM SQLite → PostgreSQL")
    parser.add_argument(
        "--sqlite",
        type=Path,
        default=_BACKEND / "data" / "repetcrm.db",
        help="Path to repetcrm.db (default: ./data/repetcrm.db)",
    )
    parser.add_argument(
        "--postgres-url",
        default=None,
        help="Target URL (default: DATABASE_URL env var)",
    )
    parser.add_argument("--dry-run", action="store_true", help="Count rows only")
    args = parser.parse_args()

    import os

    postgres_url = args.postgres_url or os.environ.get("DATABASE_URL", "")
    if not postgres_url or "postgres" not in postgres_url:
        raise SystemExit(
            "Set --postgres-url or DATABASE_URL to a postgresql+psycopg2://... URL"
        )

    migrate(args.sqlite.resolve(), postgres_url, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
