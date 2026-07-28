"""Extended dashboard widgets: upcoming lessons, debtors, inactive students, overdue HW."""

from __future__ import annotations

from datetime import date, timedelta

from sqlalchemy import and_, case, func
from sqlalchemy.orm import Session

from app.models import Homework, Lesson, LessonStatus, PaymentReceipt, Student, User
from app.schemas import (
    DashboardDebtItem,
    DashboardExtended,
    DashboardInactiveStudent,
    DashboardLessonBrief,
    DashboardOverdueHomework,
    DashboardStats,
    DashboardTrialFollowup,
    DashboardTrialLesson,
    DashboardPendingReceipt,
)
from app.services.trial_funnel_service import build_trial_followups, build_trial_lessons_this_week
from app.services.portal_student import resolve_meeting_url

INACTIVE_DAYS = 30
OVERDUE_HOMEWORK_DAYS = 3
UPCOMING_DAYS = 14


def _base_stats(db: Session, tutor_id: int, today: date, month_start: date) -> DashboardStats:
    students_count = (
        db.query(func.count(Student.id)).filter(Student.tutor_id == tutor_id).scalar() or 0
    )
    lesson_stats = (
        db.query(
            func.count(case((Lesson.lesson_date >= month_start, Lesson.id), else_=None)).label(
                "lessons_this_month"
            ),
            func.coalesce(
                func.sum(
                    case(
                        (
                            and_(Lesson.lesson_date >= month_start, Lesson.is_paid.is_(True)),
                            Lesson.payment_amount,
                        ),
                        else_=0.0,
                    )
                ),
                0.0,
            ).label("payments_this_month"),
            func.coalesce(
                func.sum(case((Lesson.is_paid.is_(False), Lesson.payment_amount), else_=0.0)),
                0.0,
            ).label("unpaid_total"),
        )
        .filter(Lesson.tutor_id == tutor_id)
        .one()
    )
    return DashboardStats(
        students_count=int(students_count),
        lessons_this_month=int(lesson_stats.lessons_this_month or 0),
        payments_this_month=float(lesson_stats.payments_this_month or 0),
        unpaid_total=float(lesson_stats.unpaid_total or 0),
    )


def build_extended_dashboard(db: Session, tutor_id: int, *, tutor_name: str = "") -> DashboardExtended:
    today = date.today()
    month_start = today.replace(day=1)
    horizon = today + timedelta(days=UPCOMING_DAYS)
    inactive_cutoff = today - timedelta(days=INACTIVE_DAYS)
    hw_cutoff = today - timedelta(days=OVERDUE_HOMEWORK_DAYS)

    stats = _base_stats(db, tutor_id, today, month_start)

    upcoming_rows = (
        db.query(Lesson, Student.name)
        .join(Student, Lesson.student_id == Student.id)
        .filter(
            Lesson.tutor_id == tutor_id,
            Lesson.lesson_date >= today,
            Lesson.lesson_date <= horizon,
            Lesson.status == LessonStatus.scheduled.value,
        )
        .order_by(Lesson.lesson_date.asc(), Lesson.lesson_time.asc())
        .limit(20)
        .all()
    )
    tutor = db.query(User).filter(User.id == tutor_id).first()
    upcoming = [
        DashboardLessonBrief(
            id=lesson.id,
            lesson_date=lesson.lesson_date,
            lesson_time=lesson.lesson_time or "10:00",
            student_id=lesson.student_id,
            student_name=name,
            duration_minutes=lesson.duration_minutes,
            is_paid=lesson.is_paid,
            payment_amount=lesson.payment_amount,
            meeting_url=resolve_meeting_url(lesson, tutor),
        )
        for lesson, name in upcoming_rows
    ]

    debtor_rows = (
        db.query(
            Student.id,
            Student.name,
            func.count(Lesson.id).label("cnt"),
            func.coalesce(func.sum(Lesson.payment_amount), 0.0).label("amount"),
        )
        .join(Lesson, Lesson.student_id == Student.id)
        .filter(
            Student.tutor_id == tutor_id,
            Lesson.tutor_id == tutor_id,
            Lesson.is_paid.is_(False),
            Lesson.payment_amount > 0,
            Lesson.lesson_date <= today,
        )
        .group_by(Student.id, Student.name)
        .order_by(func.sum(Lesson.payment_amount).desc())
        .limit(15)
        .all()
    )
    debtors = [
        DashboardDebtItem(
            student_id=sid,
            student_name=name,
            unpaid_amount=float(amount or 0),
            unpaid_lessons=int(cnt or 0),
        )
        for sid, name, cnt, amount in debtor_rows
    ]

    last_lesson_sq = (
        db.query(
            Lesson.student_id.label("student_id"),
            func.max(Lesson.lesson_date).label("last_date"),
        )
        .filter(Lesson.tutor_id == tutor_id)
        .group_by(Lesson.student_id)
        .subquery()
    )
    inactive_rows = (
        db.query(Student, last_lesson_sq.c.last_date)
        .outerjoin(last_lesson_sq, Student.id == last_lesson_sq.c.student_id)
        .filter(Student.tutor_id == tutor_id)
        .all()
    )
    inactive: list[DashboardInactiveStudent] = []
    for student, last_date in inactive_rows:
        if last_date is None:
            inactive.append(
                DashboardInactiveStudent(
                    student_id=student.id,
                    student_name=student.name,
                    last_lesson_date=None,
                    days_since=None,
                )
            )
        elif last_date < inactive_cutoff:
            inactive.append(
                DashboardInactiveStudent(
                    student_id=student.id,
                    student_name=student.name,
                    last_lesson_date=last_date,
                    days_since=(today - last_date).days,
                )
            )
    inactive.sort(key=lambda x: (x.days_since is None, -(x.days_since or 0)))
    inactive = inactive[:15]

    overdue_rows = (
        db.query(Lesson, Student.name)
        .join(Student, Lesson.student_id == Student.id)
        .outerjoin(Homework, Homework.lesson_id == Lesson.id)
        .filter(
            Lesson.tutor_id == tutor_id,
            Lesson.is_conducted.is_(True),
            Lesson.lesson_date <= hw_cutoff,
            Homework.id.is_(None),
            Lesson.status != LessonStatus.cancelled.value,
        )
        .order_by(Lesson.lesson_date.asc())
        .limit(15)
        .all()
    )
    overdue_homework = [
        DashboardOverdueHomework(
            lesson_id=lesson.id,
            lesson_date=lesson.lesson_date,
            student_id=lesson.student_id,
            student_name=name,
            days_since=(today - lesson.lesson_date).days,
        )
        for lesson, name in overdue_rows
    ]

    pending_rows = (
        db.query(PaymentReceipt, Student.name)
        .join(Student, PaymentReceipt.student_id == Student.id)
        .filter(
            PaymentReceipt.tutor_id == tutor_id,
            PaymentReceipt.status == "pending",
        )
        .order_by(PaymentReceipt.created_at.asc())
        .limit(20)
        .all()
    )
    pending_receipts = [
        DashboardPendingReceipt(
            id=receipt.id,
            student_id=receipt.student_id,
            student_name=name,
            amount=float(receipt.amount),
            original_filename=receipt.original_filename,
            parent_note=receipt.parent_note or "",
            created_at=receipt.created_at,
        )
        for receipt, name in pending_rows
    ]

    return DashboardExtended(
        stats=stats,
        upcoming_lessons=upcoming,
        debtors=debtors,
        inactive_students=inactive,
        overdue_homework=overdue_homework,
        trial_lessons_this_week=build_trial_lessons_this_week(db, tutor_id),
        trial_followups=build_trial_followups(db, tutor_id, tutor_name),
        pending_payment_receipts=pending_receipts,
    )
