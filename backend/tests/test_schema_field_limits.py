"""Schema field length validation."""

from pydantic import ValidationError

import pytest
from app.schemas import LessonCreate, StudentCreate


def test_student_name_max_length():
    with pytest.raises(ValidationError):
        StudentCreate(name="x" * 256, subject="math")


def test_student_notes_max_length():
    with pytest.raises(ValidationError):
        StudentCreate(name="Anna", notes="n" * 10001)


def test_lesson_notes_max_length():
    from datetime import date

    with pytest.raises(ValidationError):
        LessonCreate(student_id=1, lesson_date=date.today(), notes="n" * 10001)
