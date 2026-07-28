"""Helpers for tutor-scheduled trial lessons."""

from __future__ import annotations

from datetime import date

from sqlalchemy.orm import Session

from app.models import Student, TrialBooking


def apply_manual_trial_lesson(
    db: Session,
    *,
    tutor_id: int,
    student: Student,
    lesson_date: date,
    lesson_time: str,
) -> None:
    """
    Mark student as trial/lead and ensure a TrialBooking row for the CRM funnel.
    Called when tutor creates a lesson with is_trial=True.
    """
    if student.student_status not in ("trial", "lead"):
        student.student_status = "trial"

    open_statuses = ("new", "contacted", "scheduled")
    existing = (
        db.query(TrialBooking)
        .filter(
            TrialBooking.tutor_id == tutor_id,
            TrialBooking.student_id == student.id,
            TrialBooking.status.in_(open_statuses),
        )
        .order_by(TrialBooking.created_at.desc())
        .first()
    )
    if existing:
        existing.preferred_date = lesson_date
        existing.preferred_time = (lesson_time or "10:00")[:5]
        existing.status = "scheduled"
        return

    db.add(
        TrialBooking(
            tutor_id=tutor_id,
            student_id=student.id,
            preferred_date=lesson_date,
            preferred_time=(lesson_time or "10:00")[:5],
            parent_message="Пробный урок добавлен репетитором в расписание",
            status="scheduled",
        )
    )
