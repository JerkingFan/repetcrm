"""Generate lessons from recurring series."""

from __future__ import annotations

import secrets
from datetime import date, timedelta

from sqlalchemy.orm import Session

from app.models import Board, Lesson, LessonSeries, Student


def _horizon(series: LessonSeries, today: date) -> date:
    horizon = today + timedelta(weeks=max(1, series.weeks_ahead))
    if series.until_date and series.until_date < horizon:
        return series.until_date
    return horizon


def _iter_weekday_dates(start: date, end: date, weekday: int) -> list[date]:
    out: list[date] = []
    cur = start
    # align to weekday
    while cur.weekday() != weekday and cur <= end:
        cur += timedelta(days=1)
    while cur <= end:
        out.append(cur)
        cur += timedelta(days=7)
    return out


def expand_series(db: Session, series: LessonSeries, *, through: date | None = None) -> int:
    """Create missing lessons for a series up to `through`. Returns count created."""
    if not series.is_active:
        return 0

    student = db.query(Student).filter(Student.id == series.student_id).first()
    if not student:
        return 0

    today = date.today()
    end = through or _horizon(series, today)
    start = series.starts_on
    if series.last_generated_date:
        start = max(start, series.last_generated_date + timedelta(days=1))

    dates = _iter_weekday_dates(start, end, series.weekday)
    if not dates:
        return 0

    existing = {
        row[0]
        for row in db.query(Lesson.lesson_date)
        .filter(Lesson.series_id == series.id, Lesson.lesson_date >= start, Lesson.lesson_date <= end)
        .all()
    }

    created = 0
    template = (
        db.query(Lesson)
        .filter(Lesson.series_id == series.id)
        .order_by(Lesson.lesson_date.desc())
        .first()
    )
    series_meeting_url = (template.meeting_url if template else "") or ""

    for lesson_date in dates:
        if lesson_date in existing:
            continue
        board = Board(
            owner_id=series.tutor_id,
            title=f"Доска: {student.name}",
            share_token=secrets.token_urlsafe(24),
            share_writable=False,
        )
        db.add(board)
        db.flush()
        db.add(
            Lesson(
                tutor_id=series.tutor_id,
                student_id=series.student_id,
                board_id=board.id,
                series_id=series.id,
                lesson_date=lesson_date,
                lesson_time=series.lesson_time,
                duration_minutes=series.duration_minutes,
                payment_amount=series.payment_amount,
                notes=series.notes,
                meeting_url=series_meeting_url,
            )
        )
        created += 1

    if dates:
        series.last_generated_date = max(dates)
    return created


def expand_all_active_series(db: Session) -> int:
    total = 0
    for series in db.query(LessonSeries).filter(LessonSeries.is_active.is_(True)).all():
        total += expand_series(db, series)
    return total
