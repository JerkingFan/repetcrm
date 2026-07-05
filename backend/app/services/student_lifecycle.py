"""Update student lifecycle timestamps after lessons."""

from __future__ import annotations

from datetime import date, timedelta

from sqlalchemy.orm import Session

from app.models import Lesson, Student

CHURN_DAYS = 30


def touch_student_lesson_dates(db: Session, student_id: int, lesson_date: date) -> None:
    student = db.query(Student).filter(Student.id == student_id).first()
    if not student:
        return
    if student.first_lesson_at is None:
        student.first_lesson_at = lesson_date
        if student.student_status == "lead":
            student.student_status = "trial"
        elif student.student_status not in ("active", "churned"):
            student.student_status = "trial"
    student.last_lesson_at = lesson_date
    if student.student_status == "trial":
        conducted_count = (
            db.query(Lesson)
            .filter(Lesson.student_id == student_id, Lesson.is_conducted.is_(True))
            .count()
        )
        if conducted_count >= 2:
            student.student_status = "active"
    db.flush()


def refresh_student_churn_status(db: Session, tutor_id: int) -> None:
    today = date.today()
    cutoff = today - timedelta(days=CHURN_DAYS)
    students = db.query(Student).filter(Student.tutor_id == tutor_id).all()
    for s in students:
        if s.last_lesson_at is None:
            continue
        if s.last_lesson_at < cutoff and s.student_status != "churned":
            s.student_status = "churned"
        elif s.last_lesson_at >= cutoff and s.student_status == "churned":
            s.student_status = "active"
