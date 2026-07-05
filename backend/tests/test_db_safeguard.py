"""Database safeguard tests — account preservation."""

import importlib
import sqlite3
from pathlib import Path

import pytest


def _reload_config(tmp_path, monkeypatch, **env):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "data").mkdir(exist_ok=True)
    for key, val in env.items():
        monkeypatch.setenv(key, val)
    monkeypatch.setenv("REDIS_URL", "")
    monkeypatch.setenv("APP_ENV", env.get("APP_ENV", "production"))

    import app.config as config_module

    monkeypatch.setattr(config_module, "_ENV_FILE", tmp_path / "missing.env")
    importlib.reload(config_module)
    return config_module.get_settings()


def test_blocks_postgres_when_sqlite_has_users(tmp_path, monkeypatch):
    db_file = tmp_path / "data" / "repetcrm.db"
    db_file.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(db_file) as conn:
        conn.execute(
            "CREATE TABLE users (id INTEGER PRIMARY KEY, email TEXT, hashed_password TEXT)"
        )
        conn.execute(
            "INSERT INTO users (email, hashed_password) VALUES ('a@test.com', 'hash')"
        )
        conn.commit()

    cfg = _reload_config(
        tmp_path,
        monkeypatch,
        DATABASE_URL="postgresql+psycopg2://u:p@localhost/repetcrm",
        SQLITE_MIGRATION_COMPLETED="false",
    )

    from app.services import db_safeguard

    monkeypatch.setattr(db_safeguard, "default_sqlite_path", lambda: db_file)

    with pytest.raises(RuntimeError, match="Account safety"):
        db_safeguard.validate_database_switch(cfg)


def test_allows_postgres_after_migration_flag(tmp_path, monkeypatch):
    db_file = tmp_path / "data" / "repetcrm.db"
    db_file.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(db_file) as conn:
        conn.execute(
            "CREATE TABLE users (id INTEGER PRIMARY KEY, email TEXT, hashed_password TEXT)"
        )
        conn.execute(
            "INSERT INTO users (email, hashed_password) VALUES ('a@test.com', 'hash')"
        )
        conn.commit()

    cfg = _reload_config(
        tmp_path,
        monkeypatch,
        DATABASE_URL="postgresql+psycopg2://u:p@localhost/repetcrm",
        SQLITE_MIGRATION_COMPLETED="true",
    )

    from app.services import db_safeguard

    monkeypatch.setattr(db_safeguard, "default_sqlite_path", lambda: db_file)
    db_safeguard.validate_database_switch(cfg)  # must not raise


def test_production_min_users(tmp_path, monkeypatch):
    cfg = _reload_config(
        tmp_path,
        monkeypatch,
        DATABASE_URL="sqlite:///" + (tmp_path / "data" / "empty.db").as_posix(),
        PRODUCTION_MIN_USERS="3",
    )

    from app.services.db_safeguard import validate_production_user_floor

    with pytest.raises(RuntimeError, match="expected at least 3"):
        validate_production_user_floor(cfg, 1)
