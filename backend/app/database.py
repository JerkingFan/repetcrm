from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase

from app.config import settings  # noqa: E402 — used in _migrate_sqlite_columns

connect_args = {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}
engine = create_engine(settings.database_url, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _migrate_sqlite_columns():
    """Добавляет новые колонки в существующую SQLite-базу."""
    from sqlalchemy import inspect, text

    if not settings.database_url.startswith("sqlite"):
        return
    insp = inspect(engine)
    with engine.connect() as conn:
        user_cols = {c["name"] for c in insp.get_columns("users")} if insp.has_table("users") else set()
        user_add = {
            "onboarding_completed": "BOOLEAN DEFAULT 0",
            "subjects": "TEXT DEFAULT '[]'",
            "grade_levels": "TEXT DEFAULT '[]'",
            "teaching_format": "VARCHAR(50) DEFAULT ''",
        }
        for col, typedef in user_add.items():
            if col not in user_cols:
                conn.execute(text(f"ALTER TABLE users ADD COLUMN {col} {typedef}"))
        if insp.has_table("students"):
            student_cols = {c["name"] for c in insp.get_columns("students")}
            student_add = {
                "grade": "VARCHAR(50) DEFAULT ''",
                "school": "VARCHAR(255) DEFAULT ''",
                "parent_contact": "VARCHAR(255) DEFAULT ''",
                "notes": "TEXT DEFAULT ''",
            }
            for col, typedef in student_add.items():
                if col not in student_cols:
                    conn.execute(text(f"ALTER TABLE students ADD COLUMN {col} {typedef}"))
        if insp.has_table("lessons"):
            lesson_cols = {c["name"] for c in insp.get_columns("lessons")}
            if "lesson_time" not in lesson_cols:
                conn.execute(
                    text("ALTER TABLE lessons ADD COLUMN lesson_time VARCHAR(5) DEFAULT '10:00'")
                )
            if "is_conducted" not in lesson_cols:
                conn.execute(
                    text("ALTER TABLE lessons ADD COLUMN is_conducted BOOLEAN DEFAULT 0")
                )
            if "homework_prefs" not in lesson_cols:
                conn.execute(text("ALTER TABLE lessons ADD COLUMN homework_prefs TEXT DEFAULT ''"))
            if "board_id" not in lesson_cols:
                conn.execute(text("ALTER TABLE lessons ADD COLUMN board_id INTEGER"))
        conn.commit()


def init_db():
    from app import models  # noqa: F401

    Base.metadata.create_all(bind=engine)
    _migrate_sqlite_columns()
