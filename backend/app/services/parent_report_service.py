"""Monthly parent report data aggregation."""

from __future__ import annotations

from calendar import monthrange
from datetime import date, datetime

from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from app.models import (
    ChecklistItem,
    Homework,
    HomeworkSubmission,
    Lesson,
    PaymentTransaction,
    Student,
    User,
)
from app.schemas import (
    ParentMonthlyReportOut,
    ParentReportHomeworkItem,
    ParentReportLessonItem,
)
from app.services.homework_submission_review import latest_submission_status, status_label


def current_month_str() -> str:
    today = date.today()
    return f"{today.year:04d}-{today.month:02d}"


def resolve_month(month: str | None) -> str:
    key = (month or current_month_str()).strip()
    parse_month(key)
    return key


def parse_month(month: str) -> tuple[date, date]:
    parts = (month or "").strip().split("-")
    if len(parts) != 2:
        raise ValueError("month must be YYYY-MM")
    year, mon = int(parts[0]), int(parts[1])
    if mon < 1 or mon > 12:
        raise ValueError("invalid month")
    start = date(year, mon, 1)
    last = monthrange(year, mon)[1]
    end = date(year, mon, last)
    return start, end


def _month_label(month: str) -> str:
    year, mon = map(int, month.split("-"))
    names = [
        "",
        "январь",
        "февраль",
        "март",
        "апрель",
        "май",
        "июнь",
        "июль",
        "август",
        "сентябрь",
        "октябрь",
        "ноябрь",
        "декабрь",
    ]
    return f"{names[mon]} {year}"


def build_parent_monthly_report(
    db: Session,
    *,
    student: Student,
    tutor: User,
    month: str,
) -> ParentMonthlyReportOut:
    start, end = parse_month(month)
    lessons = (
        db.query(Lesson)
        .filter(
            Lesson.student_id == student.id,
            Lesson.tutor_id == student.tutor_id,
            Lesson.lesson_date >= start,
            Lesson.lesson_date <= end,
        )
        .order_by(Lesson.lesson_date.asc(), Lesson.lesson_time.asc())
        .all()
    )

    lesson_items = [
        ParentReportLessonItem(
            lesson_date=l.lesson_date,
            lesson_time=l.lesson_time or "10:00",
            is_conducted=bool(l.is_conducted),
            is_paid=bool(l.is_paid),
            payment_amount=float(l.payment_amount or 0),
        )
        for l in lessons
    ]
    conducted = sum(1 for l in lessons if l.is_conducted)

    hw_rows = (
        db.query(Homework, Lesson.lesson_date)
        .join(Lesson, Homework.lesson_id == Lesson.id)
        .filter(
            Lesson.student_id == student.id,
            Lesson.lesson_date >= start,
            Lesson.lesson_date <= end,
        )
        .order_by(Lesson.lesson_date.desc())
        .all()
    )
    hw_ids = [hw.id for hw, _ in hw_rows]
    subs_by_hw: dict[int, list[HomeworkSubmission]] = {}
    if hw_ids:
        for sub in (
            db.query(HomeworkSubmission)
            .filter(
                HomeworkSubmission.homework_id.in_(hw_ids),
                HomeworkSubmission.student_id == student.id,
            )
            .all()
        ):
            subs_by_hw.setdefault(sub.homework_id, []).append(sub)

    homework_items = []
    for hw, lesson_date in hw_rows:
        subs = subs_by_hw.get(hw.id, [])
        status = latest_submission_status(subs)
        homework_items.append(
            ParentReportHomeworkItem(
                lesson_date=lesson_date,
                status=status,
                status_label=status_label(status),
            )
        )

    topics: list[str] = []
    if lessons:
        lesson_ids = [l.id for l in lessons]
        for row in (
            db.query(ChecklistItem.topic)
            .filter(ChecklistItem.lesson_id.in_(lesson_ids))
            .order_by(ChecklistItem.id.asc())
            .all()
        ):
            topic = (row.topic or "").strip()
            if topic and topic not in topics:
                topics.append(topic)

    from datetime import datetime, time

    start_dt = datetime.combine(start, time.min)
    end_dt = datetime.combine(end, time.max)
    payments_total = (
        db.query(func.coalesce(func.sum(PaymentTransaction.amount), 0.0))
        .filter(
            PaymentTransaction.student_id == student.id,
            PaymentTransaction.tutor_id == student.tutor_id,
            PaymentTransaction.status == "paid",
            PaymentTransaction.created_at >= start_dt,
            PaymentTransaction.created_at <= end_dt,
        )
        .scalar()
    )

    month_label = _month_label(month)
    homework_done = sum(1 for h in homework_items if h.status in ("submitted", "reviewed"))
    homework_total = len(homework_items)
    done_pct = int(round(100 * homework_done / homework_total)) if homework_total else 0

    if conducted and topics:
        tutor_note = (
            f"За {month_label.split()[0]} прошли: {', '.join(topics[:3])}"
            + ("…" if len(topics) > 3 else "")
            + f". Домашние сданы на {done_pct}%."
        )
    elif conducted:
        tutor_note = f"Проведено уроков: {conducted}. ДЗ сдано на {done_pct}%."
    else:
        tutor_note = "В этом месяце уроков пока не было."

    snapshot_line = (
        f"{conducted} ур. · ДЗ {done_pct}% · "
        + (topics[0] if topics else "темы появятся после занятий")
    )

    return ParentMonthlyReportOut(
        month=month,
        month_label=month_label,
        student_name=student.name,
        tutor_name=tutor.name or "",
        subject=student.subject or "",
        grade=student.grade or "",
        lessons_total=len(lessons),
        lessons_conducted=conducted,
        lessons=lesson_items,
        homework=homework_items,
        topics_covered=topics[:30],
        payments_total=float(payments_total or 0),
        balance=float(student.balance or 0),
        homework_total=homework_total,
        homework_done_pct=done_pct,
        tutor_note=tutor_note,
        snapshot_line=snapshot_line,
    )


def load_student_for_tutor(db: Session, student_id: int, tutor_id: int) -> Student | None:
    return (
        db.query(Student)
        .filter(Student.id == student_id, Student.tutor_id == tutor_id)
        .first()
    )


def load_tutor(db: Session, tutor_id: int) -> User | None:
    return db.query(User).filter(User.id == tutor_id).first()
