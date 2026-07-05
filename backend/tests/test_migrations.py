"""Alembic migration integration tests."""

import importlib
import uuid
from pathlib import Path

from sqlalchemy import inspect


def _reload_db_stack(tmp_path, monkeypatch, db_name: str):
    db_path = tmp_path / db_name
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path.as_posix()}")
    monkeypatch.setenv("REDIS_URL", "")

    import app.config as config_module

    monkeypatch.setattr(config_module, "_ENV_FILE", tmp_path / "missing.env")

    import app.database as database_module
    import app.db_migrate as migrate_module

    importlib.reload(config_module)
    importlib.reload(database_module)
    importlib.reload(migrate_module)
    return database_module


def test_fresh_database_runs_migrations(tmp_path, monkeypatch):
    db = _reload_db_stack(tmp_path, monkeypatch, f"fresh_{uuid.uuid4().hex}.db")
    db.init_db()

    insp = inspect(db.engine)
    assert insp.has_table("users")
    assert insp.has_table("boards")
    assert insp.has_table("auth_sessions")
    assert insp.has_table("alembic_version")

    rev = db.engine.connect().execute(
        __import__("sqlalchemy").text("SELECT version_num FROM alembic_version")
    ).scalar_one()
    assert rev == "f3a4b5c6d7e8"


def test_existing_database_upgrades_preserving_users(tmp_path, monkeypatch):
    """DB at previous Alembic revision migrates forward without data loss."""
    db = _reload_db_stack(tmp_path, monkeypatch, f"legacy_{uuid.uuid4().hex}.db")

    from alembic import command
    from alembic.config import Config

    ini = Path(__file__).resolve().parent.parent / "alembic.ini"
    cfg = Config(str(ini))
    cfg.set_main_option("sqlalchemy.url", f"sqlite:///{db.engine.url.database}")
    command.upgrade(cfg, "d5e6f7a8b9c0")

    with db.engine.connect() as conn:
        conn.execute(
            __import__("sqlalchemy").text(
                "INSERT INTO users (email, hashed_password, name, onboarding_completed, "
                "subjects, grade_levels, teaching_format, created_at) "
                "VALUES ('legacy@test.example', 'hash', 'Legacy', 0, '[]', '[]', '', datetime('now'))"
            )
        )
        conn.commit()

    db.init_db()

    with db.engine.connect() as conn:
        count = conn.execute(__import__("sqlalchemy").text("SELECT COUNT(*) FROM users")).scalar_one()
        rev = conn.execute(
            __import__("sqlalchemy").text("SELECT version_num FROM alembic_version")
        ).scalar_one()

    assert count == 1
    assert rev == "f3a4b5c6d7e8"
