from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase

from app.config import settings  # noqa: E402 — used in _migrate_sqlite_columns

_is_sqlite = settings.database_url.startswith("sqlite")

_engine_kwargs: dict = {}
if _is_sqlite:
    _engine_kwargs["connect_args"] = {"check_same_thread": False}
else:
    _engine_kwargs.update(
        pool_size=settings.db_pool_size,
        max_overflow=settings.db_max_overflow,
        pool_timeout=settings.db_pool_timeout,
        pool_recycle=settings.db_pool_recycle,
        pool_pre_ping=True,
    )

engine = create_engine(settings.database_url, **_engine_kwargs)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _sqlite_add_column(conn, table: str, col: str, typedef: str) -> bool:
    """ADD COLUMN; returns True if column was added. Ignores duplicate-column errors."""
    from sqlalchemy import text
    from sqlalchemy.exc import OperationalError

    try:
        conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {col} {typedef}"))
        return True
    except OperationalError as exc:
        if "duplicate column" in str(exc).lower():
            return False
        raise


def _migrate_sqlite_columns():
    """Добавляет новые колонки в существующую SQLite-базу."""
    from sqlalchemy import inspect, text

    if not settings.database_url.startswith("sqlite"):
        return
    insp = inspect(engine)
    with engine.connect() as conn:
        if insp.has_table("users"):
            user_cols = {c["name"] for c in insp.get_columns("users")}
            user_add = {
                "onboarding_completed": "BOOLEAN DEFAULT 0",
                "subjects": "TEXT DEFAULT '[]'",
                "grade_levels": "TEXT DEFAULT '[]'",
                "teaching_format": "VARCHAR(50) DEFAULT ''",
            }
            for col, typedef in user_add.items():
                if col not in user_cols:
                    _sqlite_add_column(conn, "users", col, typedef)

        if insp.has_table("students"):
            student_cols = {c["name"] for c in insp.get_columns("students")}
            student_add = {
                "grade": "VARCHAR(50) DEFAULT ''",
                "school": "VARCHAR(255) DEFAULT ''",
                "parent_contact": "VARCHAR(255) DEFAULT ''",
                "notes": "TEXT DEFAULT ''",
                "boundary_mode": "VARCHAR(20) DEFAULT 'normal'",
                "boundary_reason": "TEXT DEFAULT ''",
            }
            for col, typedef in student_add.items():
                if col not in student_cols:
                    _sqlite_add_column(conn, "students", col, typedef)
            # SQLite: non-constant DEFAULT (CURRENT_TIMESTAMP) запрещён в ALTER TABLE
            if "boundary_updated_at" not in student_cols:
                _sqlite_add_column(conn, "students", "boundary_updated_at", "DATETIME")
                conn.execute(
                    text(
                        "UPDATE students SET boundary_updated_at = "
                        "COALESCE(created_at, datetime('now')) WHERE boundary_updated_at IS NULL"
                    )
                )

        if insp.has_table("lessons"):
            lesson_cols = {c["name"] for c in insp.get_columns("lessons")}
            if "lesson_time" not in lesson_cols:
                _sqlite_add_column(conn, "lessons", "lesson_time", "VARCHAR(5) DEFAULT '10:00'")
            if "is_conducted" not in lesson_cols:
                _sqlite_add_column(conn, "lessons", "is_conducted", "BOOLEAN DEFAULT 0")
            if "homework_prefs" not in lesson_cols:
                _sqlite_add_column(conn, "lessons", "homework_prefs", "TEXT DEFAULT ''")
            if "board_id" not in lesson_cols:
                _sqlite_add_column(conn, "lessons", "board_id", "INTEGER")
            lesson_add = {
                "status": "VARCHAR(20) DEFAULT 'scheduled'",
                "late_minutes": "INTEGER DEFAULT 0",
                "rescheduled_from_lesson_id": "INTEGER",
            }
            for col, typedef in lesson_add.items():
                if col not in lesson_cols:
                    _sqlite_add_column(conn, "lessons", col, typedef)
            if "status_changed_at" not in lesson_cols:
                _sqlite_add_column(conn, "lessons", "status_changed_at", "DATETIME")
                conn.execute(
                    text(
                        "UPDATE lessons SET status_changed_at = "
                        "COALESCE(created_at, datetime('now')) WHERE status_changed_at IS NULL"
                    )
                )
        conn.commit()


def _ensure_performance_indexes():
    """Создаёт индексы на существующих БД (идемпотентно)."""
    from sqlalchemy import inspect, text

    insp = inspect(engine)
    if not insp.has_table("lessons"):
        return
    indexes = [
        "CREATE INDEX IF NOT EXISTS idx_students_tutor_name ON students(tutor_id, name)",
        "CREATE INDEX IF NOT EXISTS idx_lessons_tutor_date ON lessons(tutor_id, lesson_date)",
        "CREATE INDEX IF NOT EXISTS idx_lessons_tutor_date_desc ON lessons(tutor_id, lesson_date DESC)",
        "CREATE INDEX IF NOT EXISTS idx_lessons_tutor_paid ON lessons(tutor_id, is_paid)",
        "CREATE INDEX IF NOT EXISTS idx_lessons_student_date ON lessons(student_id, lesson_date DESC)",
        "CREATE INDEX IF NOT EXISTS idx_auth_sessions_user_id ON auth_sessions(user_id)",
        "CREATE INDEX IF NOT EXISTS idx_auth_sessions_token_hash ON auth_sessions(token_hash)",
    ]
    with engine.connect() as conn:
        for ddl in indexes:
            try:
                conn.execute(text(ddl))
            except Exception:
                pass
        conn.commit()


def init_db():
    from app import models  # noqa: F401

    Base.metadata.create_all(bind=engine)
    _migrate_sqlite_columns()
    _ensure_performance_indexes()
