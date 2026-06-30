"""Student name search helpers (pg_trgm on PostgreSQL, ILIKE on SQLite)."""

from __future__ import annotations

from sqlalchemy.orm import Query

from app.database import engine
from app.models import Student


def is_postgresql() -> bool:
    return engine.dialect.name == "postgresql"


def apply_student_name_search(query: Query, tutor_id: int, q: str | None) -> Query:
    query = query.filter(Student.tutor_id == tutor_id)
    term = (q or "").strip()
    if not term:
        return query
    # PostgreSQL uses GIN pg_trgm index (see migrations); SQLite falls back to table scan.
    return query.filter(Student.name.ilike(f"%{term}%"))
