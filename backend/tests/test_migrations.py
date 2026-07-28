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
    import app.models as models_module

    importlib.reload(config_module)
    importlib.reload(database_module)
    importlib.reload(models_module)
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
    assert rev == "c3d4e5f6a7b8"


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
    assert rev == "c3d4e5f6a7b8"


def test_repair_users_columns_allows_orm_load(tmp_path, monkeypatch):
    """Missing notify_* / payment_details on users must not break login SELECT."""
    db = _reload_db_stack(tmp_path, monkeypatch, f"min_user_{uuid.uuid4().hex}.db")

    with db.engine.connect() as conn:
        conn.execute(
            __import__("sqlalchemy").text(
                """
                CREATE TABLE users (
                    id INTEGER NOT NULL PRIMARY KEY,
                    email VARCHAR(255) NOT NULL UNIQUE,
                    hashed_password VARCHAR(255) NOT NULL,
                    name VARCHAR(255) NOT NULL DEFAULT '',
                    onboarding_completed BOOLEAN NOT NULL DEFAULT 0,
                    subjects TEXT NOT NULL DEFAULT '[]',
                    grade_levels TEXT NOT NULL DEFAULT '[]',
                    teaching_format VARCHAR(50) NOT NULL DEFAULT '',
                    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
        )
        conn.commit()

    from app.db_migrate import repair_legacy_schema
    from app.models import User

    repair_legacy_schema()

    session = db.SessionLocal()
    try:
        session.add(
            User(
                email="tutor@test.example",
                hashed_password="x",
                name="T",
            )
        )
        session.commit()
        loaded = session.query(User).filter(User.email == "tutor@test.example").one()
        assert loaded.notify_email is True
        assert loaded.payment_details == ""
    finally:
        session.close()


def test_repair_creates_auth_sessions_for_legacy_users_db(tmp_path, monkeypatch):
    """Users without auth_sessions (old create_all DB) — login must not 500."""
    db = _reload_db_stack(tmp_path, monkeypatch, f"no_sess_{uuid.uuid4().hex}.db")

    with db.engine.connect() as conn:
        conn.execute(
            __import__("sqlalchemy").text(
                """
                CREATE TABLE users (
                    id INTEGER NOT NULL PRIMARY KEY,
                    email VARCHAR(255) NOT NULL UNIQUE,
                    hashed_password VARCHAR(255) NOT NULL,
                    name VARCHAR(255) NOT NULL DEFAULT '',
                    onboarding_completed BOOLEAN NOT NULL DEFAULT 0,
                    subjects TEXT NOT NULL DEFAULT '[]',
                    grade_levels TEXT NOT NULL DEFAULT '[]',
                    teaching_format VARCHAR(50) NOT NULL DEFAULT '',
                    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
        )
        conn.commit()

    from app.db_migrate import repair_legacy_schema

    repair_legacy_schema()

    insp = inspect(db.engine)
    assert insp.has_table("auth_sessions")


def test_legacy_db_without_alembic_version_stamps_then_upgrades(tmp_path, monkeypatch):
    """Populated DB without alembic_version must not replay initial_schema."""
    db = _reload_db_stack(tmp_path, monkeypatch, f"no_ver_{uuid.uuid4().hex}.db")

    from alembic import command
    from alembic.config import Config

    ini = Path(__file__).resolve().parent.parent / "alembic.ini"
    cfg = Config(str(ini))
    cfg.set_main_option("sqlalchemy.url", f"sqlite:///{db.engine.url.database}")
    command.upgrade(cfg, "e2f3a4b5c6d7")

    with db.engine.connect() as conn:
        conn.execute(
            __import__("sqlalchemy").text(
                "INSERT INTO users (email, hashed_password, name, onboarding_completed, "
                "subjects, grade_levels, teaching_format, created_at) "
                "VALUES ('legacy@test.example', 'hash', 'Legacy', 0, '[]', '[]', '', datetime('now'))"
            )
        )
        conn.execute(__import__("sqlalchemy").text("DROP TABLE alembic_version"))
        conn.commit()

    db.init_db()

    insp = inspect(db.engine)
    assert insp.has_table("payment_receipts")
    with db.engine.connect() as conn:
        count = conn.execute(__import__("sqlalchemy").text("SELECT COUNT(*) FROM users")).scalar_one()
        rev = conn.execute(
            __import__("sqlalchemy").text("SELECT version_num FROM alembic_version")
        ).scalar_one()

    assert count == 1
    assert rev == "c3d4e5f6a7b8"


def test_repair_boards_share_writable_and_snapshots(tmp_path, monkeypatch):
    """Old boards table without share_writable must not 500 on GET /boards/:id."""
    db = _reload_db_stack(tmp_path, monkeypatch, f"boards_{uuid.uuid4().hex}.db")

    with db.engine.connect() as conn:
        conn.execute(
            __import__("sqlalchemy").text(
                """
                CREATE TABLE users (
                    id INTEGER NOT NULL PRIMARY KEY,
                    email VARCHAR(255) NOT NULL UNIQUE,
                    hashed_password VARCHAR(255) NOT NULL,
                    name VARCHAR(255) NOT NULL DEFAULT '',
                    onboarding_completed BOOLEAN NOT NULL DEFAULT 0,
                    subjects TEXT NOT NULL DEFAULT '[]',
                    grade_levels TEXT NOT NULL DEFAULT '[]',
                    teaching_format VARCHAR(50) NOT NULL DEFAULT '',
                    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
        )
        conn.execute(
            __import__("sqlalchemy").text(
                """
                CREATE TABLE boards (
                    id INTEGER NOT NULL PRIMARY KEY,
                    owner_id INTEGER NOT NULL,
                    title VARCHAR(255) NOT NULL DEFAULT 'Виртуальная доска',
                    share_token VARCHAR(64) NOT NULL UNIQUE,
                    state_json TEXT NOT NULL DEFAULT '{}',
                    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(owner_id) REFERENCES users (id)
                )
                """
            )
        )
        conn.commit()

    from app.db_migrate import repair_legacy_schema
    from app.models import Board, User

    repair_legacy_schema()

    insp = inspect(db.engine)
    assert insp.has_table("board_snapshots")
    board_cols = {c["name"] for c in insp.get_columns("boards")}
    assert "share_writable" in board_cols

    session = db.SessionLocal()
    try:
        user = User(email="tutor@test.example", hashed_password="x", name="T")
        session.add(user)
        session.commit()
        board = Board(owner_id=user.id, share_token="tok123", title="Test")
        session.add(board)
        session.commit()
        loaded = session.query(Board).filter(Board.id == board.id).one()
        assert loaded.share_writable is True
    finally:
        session.close()
