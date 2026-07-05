"""Daily reminder jobs (ARQ cron)."""

from __future__ import annotations

import logging
from datetime import date, timedelta

from sqlalchemy.orm import Session, joinedload

from app.database import SessionLocal
from app.models import Lesson, LessonStatus, Student, User
from app.services.lesson_recurrence import expand_all_active_series
from app.services.notifications import notify_user
from app.services.parent_notifications import (
    lesson_price_hint,
    notify_parent_lesson_tomorrow,
    notify_parent_low_balance,
)

logger = logging.getLogger(__name__)


def _send_lesson_tomorrow(db: Session) -> int:
    tomorrow = date.today() + timedelta(days=1)
    sent = 0
    rows = (
        db.query(Lesson)
        .options(joinedload(Lesson.student))
        .join(User, User.id == Lesson.tutor_id)
        .filter(
            Lesson.lesson_date == tomorrow,
            Lesson.status == LessonStatus.scheduled.value,
            User.notify_lesson_tomorrow.is_(True),
        )
        .all()
    )
    for lesson in rows:
        user = db.query(User).filter(User.id == lesson.tutor_id).first()
        if not user:
            continue
        name = lesson.student.name if lesson.student else "ученик"
        ref_key = f"lesson_tomorrow:{lesson.id}:{tomorrow.isoformat()}"
        subject = "RepetCRM: урок завтра"
        body = (
            f"Завтра урок с {name} в {lesson.lesson_time} "
            f"({lesson.duration_minutes} мин)."
        )
        if notify_user(db, user, kind="lesson_tomorrow", ref_key=ref_key, subject=subject, body=body):
            sent += 1
    return sent


def _send_parent_lesson_tomorrow(db: Session) -> int:
    tomorrow = date.today() + timedelta(days=1)
    sent = 0
    rows = (
        db.query(Lesson)
        .options(joinedload(Lesson.student))
        .filter(
            Lesson.lesson_date == tomorrow,
            Lesson.status == LessonStatus.scheduled.value,
        )
        .all()
    )
    for lesson in rows:
        student = lesson.student
        if not student:
            continue
        tutor = db.query(User).filter(User.id == lesson.tutor_id).first()
        if not tutor:
            continue
        if notify_parent_lesson_tomorrow(
            db,
            lesson=lesson,
            student=student,
            tutor=tutor,
            lesson_date_iso=tomorrow.isoformat(),
        ):
            sent += 1
    return sent


def _send_parent_low_balance(db: Session) -> int:
    today = date.today()
    sent = 0
    students = (
        db.query(Student)
        .filter(Student.parent_notify_email.is_(True))
        .all()
    )
    for student in students:
        email = (student.parent_email or "").strip()
        if not email or "@" not in email:
            continue
        tutor = db.query(User).filter(User.id == student.tutor_id).first()
        if not tutor:
            continue
        price = lesson_price_hint(db, student, student.tutor_id)
        if price <= 0:
            continue
        balance = float(student.balance or 0)
        if balance >= price:
            continue
        if notify_parent_low_balance(
            db,
            student=student,
            tutor=tutor,
            lesson_price=price,
            day_iso=today.isoformat(),
        ):
            sent += 1
    return sent


def _send_unpaid_reminders(db: Session) -> int:
    today = date.today()
    sent = 0
    rows = (
        db.query(Lesson)
        .options(joinedload(Lesson.student))
        .join(User, User.id == Lesson.tutor_id)
        .filter(
            Lesson.is_paid.is_(False),
            Lesson.payment_amount > 0,
            Lesson.lesson_date <= today,
            User.notify_unpaid.is_(True),
        )
        .all()
    )
    for lesson in rows:
        if lesson.status not in (LessonStatus.completed.value, LessonStatus.scheduled.value):
            if not lesson.is_conducted:
                continue
        user = db.query(User).filter(User.id == lesson.tutor_id).first()
        if not user:
            continue
        name = lesson.student.name if lesson.student else "ученик"
        ref_key = f"unpaid:{lesson.id}"
        subject = "RepetCRM: неоплаченный урок"
        body = (
            f"Урок с {name} ({lesson.lesson_date.isoformat()}) — "
            f"не оплачен ({lesson.payment_amount})."
        )
        if notify_user(db, user, kind="unpaid", ref_key=ref_key, subject=subject, body=body):
            sent += 1
    return sent


async def run_daily_reminders(ctx) -> dict:
    db = SessionLocal()
    try:
        expanded = expand_all_active_series(db)
        tomorrow_n = _send_lesson_tomorrow(db)
        parent_tomorrow_n = _send_parent_lesson_tomorrow(db)
        parent_balance_n = _send_parent_low_balance(db)
        unpaid_n = _send_unpaid_reminders(db)
        db.commit()
        result = {
            "series_lessons_created": expanded,
            "lesson_tomorrow_sent": tomorrow_n,
            "parent_lesson_tomorrow_sent": parent_tomorrow_n,
            "parent_low_balance_sent": parent_balance_n,
            "unpaid_sent": unpaid_n,
        }
        logger.info("daily reminders: %s", result)
        return result
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
