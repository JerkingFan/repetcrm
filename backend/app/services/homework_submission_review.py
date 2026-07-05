"""Homework submission review helpers."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy.orm import Session

from app.models import Homework, HomeworkSubmission, Student, User

STATUS_LABELS: dict[str, str] = {
    "not_submitted": "Не сдано",
    "submitted": "На проверке",
    "reviewed": "Проверено",
    "needs_revision": "Нужна доработка",
}


def status_label(status: str) -> str:
    return STATUS_LABELS.get(status, status)


def latest_submission_status(submissions: list[HomeworkSubmission]) -> str:
    if not submissions:
        return "not_submitted"
    latest = max(submissions, key=lambda s: s.submitted_at or datetime.min)
    return (latest.status or "submitted").strip() or "submitted"


def review_submission(
    db: Session,
    *,
    submission: HomeworkSubmission,
    homework: Homework,
    tutor: User,
    status: str,
    tutor_comment: str,
) -> HomeworkSubmission:
    submission.status = status
    submission.tutor_comment = (tutor_comment or "").strip()[:2000]
    submission.reviewed_at = datetime.utcnow()
    db.flush()

    student = db.query(Student).filter(Student.id == submission.student_id).first()
    if student and status == "reviewed":
        from app.services.parent_notifications import notify_parent_homework_reviewed

        notify_parent_homework_reviewed(
            db,
            student=student,
            tutor=tutor,
            homework=homework,
            submission=submission,
        )
    return submission
