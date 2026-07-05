"""Trial → regular student funnel: dashboard widgets and follow-up messages."""

from __future__ import annotations

from datetime import date, timedelta

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models import Lesson, LessonPackage, LessonStatus, Student
from app.schemas import (
    DashboardTrialFollowup,
    DashboardTrialLesson,
    TrialFollowupOut,
)
from app.services.parent_notifications import parent_portal_url

DEFAULT_PACKAGE_LESSONS = 8


def week_bounds(today: date | None = None) -> tuple[date, date]:
    today = today or date.today()
    start = today - timedelta(days=today.weekday())
    return start, start + timedelta(days=6)


def conducted_lessons_count(db: Session, student_id: int) -> int:
    return (
        db.query(func.count(Lesson.id))
        .filter(Lesson.student_id == student_id, Lesson.is_conducted.is_(True))
        .scalar()
        or 0
    )


def _package_offer(db: Session, student: Student) -> tuple[int, float, str]:
    pkg = (
        db.query(LessonPackage)
        .filter(
            LessonPackage.student_id == student.id,
            LessonPackage.is_active.is_(True),
        )
        .order_by(LessonPackage.created_at.desc())
        .first()
    )
    if pkg:
        return (
            int(pkg.lessons_total),
            float(pkg.price_per_lesson or 0),
            pkg.name or f"{pkg.lessons_total} занятий",
        )
    last_price = (
        db.query(Lesson.payment_amount)
        .filter(Lesson.student_id == student.id, Lesson.payment_amount > 0)
        .order_by(Lesson.lesson_date.desc())
        .first()
    )
    price = float(last_price[0]) if last_price else 50.0
    return DEFAULT_PACKAGE_LESSONS, price, f"абонемент на {DEFAULT_PACKAGE_LESSONS} занятий"


def build_trial_followup_message(db: Session, student: Student, tutor_name: str) -> str:
    portal = parent_portal_url(db, student)
    lessons_n, price, pkg_label = _package_offer(db, student)
    total = round(lessons_n * price, 2)
    parent_line = f", {student.parent_name}" if student.parent_name else ""
    greeting = f"Здравствуйте{parent_line}!\n\n"
    body = (
        f"Спасибо за пробное занятие с {student.name}.\n\n"
        f"Кабинет родителя — расписание, баланс и оплата онлайн:\n{portal}\n\n"
        f"Предлагаю {pkg_label} по {price:.0f} Br за урок (итого {total:.0f} Br).\n"
        f"Оплатить можно в кабинете по ссылке выше.\n\n"
        f"С уважением,\n{tutor_name or 'Ваш репетитор'}"
    )
    return greeting + body


def should_show_trial_followup(db: Session, student: Student) -> bool:
    if student.student_status not in ("trial", "lead"):
        return False
    return conducted_lessons_count(db, student.id) == 1


def get_trial_followup(db: Session, student: Student, tutor_name: str) -> TrialFollowupOut:
    show = should_show_trial_followup(db, student)
    message = build_trial_followup_message(db, student, tutor_name) if show else ""
    return TrialFollowupOut(
        show=show,
        message=message,
        parent_portal_url=parent_portal_url(db, student) if show else "",
        student_name=student.name,
        conducted_lessons=conducted_lessons_count(db, student.id),
    )


def build_trial_lessons_this_week(db: Session, tutor_id: int) -> list[DashboardTrialLesson]:
    today = date.today()
    week_start, week_end = week_bounds(today)
    rows = (
        db.query(Lesson, Student)
        .join(Student, Lesson.student_id == Student.id)
        .filter(
            Lesson.tutor_id == tutor_id,
            Student.tutor_id == tutor_id,
            Student.student_status.in_(("trial", "lead")),
            Lesson.lesson_date >= week_start,
            Lesson.lesson_date <= week_end,
            Lesson.status != LessonStatus.cancelled.value,
        )
        .order_by(Lesson.lesson_date.asc(), Lesson.lesson_time.asc())
        .limit(20)
        .all()
    )
    out: list[DashboardTrialLesson] = []
    for lesson, student in rows:
        out.append(
            DashboardTrialLesson(
                lesson_id=lesson.id,
                student_id=student.id,
                student_name=student.name,
                lesson_date=lesson.lesson_date,
                lesson_time=lesson.lesson_time or "10:00",
                is_conducted=bool(lesson.is_conducted),
                student_status=student.student_status,
                conducted_lessons=conducted_lessons_count(db, student.id),
            )
        )
    return out


def build_trial_followups(db: Session, tutor_id: int, tutor_name: str) -> list[DashboardTrialFollowup]:
    students = (
        db.query(Student)
        .filter(
            Student.tutor_id == tutor_id,
            Student.student_status.in_(("trial", "lead")),
        )
        .order_by(Student.name.asc())
        .all()
    )
    out: list[DashboardTrialFollowup] = []
    for student in students:
        if not should_show_trial_followup(db, student):
            continue
        out.append(
            DashboardTrialFollowup(
                student_id=student.id,
                student_name=student.name,
                parent_name=student.parent_name or "",
                conducted_lessons=1,
                message=build_trial_followup_message(db, student, tutor_name),
            )
        )
    return out[:15]
