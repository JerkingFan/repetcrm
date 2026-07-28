"""iCalendar export for tutors and parents."""

from __future__ import annotations

from datetime import date, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy.orm import Session, joinedload

from app.config import get_settings
from app.database import get_db

router = APIRouter(prefix="/calendar", tags=["calendar"])


@router.get("/tutor.ics")
def tutor_calendar_ics(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    from_date: date | None = Query(None, alias="from"),
    to_date: date | None = Query(None, alias="to"),
):
    today = date.today()
    start = from_date or today - timedelta(days=7)
    end = to_date or today + timedelta(days=90)
    lessons = (
        db.query(Lesson)
        .options(joinedload(Lesson.student))
        .filter(
            Lesson.tutor_id == user.id,
            Lesson.lesson_date >= start,
            Lesson.lesson_date <= end,
            Lesson.status != LessonStatus.cancelled.value,
        )
        .order_by(Lesson.lesson_date.asc(), Lesson.lesson_time.asc())
        .all()
    )
    body = build_ics(
        lessons,
        calendar_name=f"RepetCRM — {user.name or 'Репетитор'}",
        meeting_url_for=lambda l: resolve_meeting_url(l, user),
    )
    return Response(
        content=body.encode("utf-8"),
        media_type="text/calendar; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="tutor-schedule.ics"'},
    )


@router.get("/student/{student_id}.ics")
def student_calendar_ics_for_tutor(
    student_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    from_date: date | None = Query(None, alias="from"),
    to_date: date | None = Query(None, alias="to"),
):
    student = db.query(Student).filter(Student.id == student_id, Student.tutor_id == user.id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    today = date.today()
    start = from_date or today - timedelta(days=7)
    end = to_date or today + timedelta(days=90)
    lessons = (
        db.query(Lesson)
        .filter(
            Lesson.student_id == student.id,
            Lesson.lesson_date >= start,
            Lesson.lesson_date <= end,
            Lesson.status != LessonStatus.cancelled.value,
        )
        .order_by(Lesson.lesson_date.asc())
        .all()
    )
    body = build_ics(
        lessons,
        calendar_name=f"Занятия — {student.name}",
        student_name=student.name,
        meeting_url_for=lambda l: resolve_meeting_url(l, user),
    )
    return Response(
        content=body.encode("utf-8"),
        media_type="text/calendar; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="student-{student_id}.ics"'},
    )


@router.get("/feed.ics")
def calendar_feed_by_portal_token(
    token: str = Query(..., min_length=16),
    db: Session = Depends(get_db),
):
    """Subscribe URL for Google/Apple Calendar (parent/student link, no login)."""
    student = student_by_any_portal_token(db, token)
    if not student:
        raise HTTPException(status_code=404, detail="Invalid token")
    today = date.today()
    lessons = (
        db.query(Lesson)
        .filter(
            Lesson.student_id == student.id,
            Lesson.lesson_date >= today - timedelta(days=30),
            Lesson.status != LessonStatus.cancelled.value,
        )
        .order_by(Lesson.lesson_date.asc())
        .all()
    )
    tutor = db.query(User).filter(User.id == student.tutor_id).first()
    body = build_ics(
        lessons,
        calendar_name=f"Занятия — {student.name}",
        student_name=student.name,
        meeting_url_for=lambda l: resolve_meeting_url(l, tutor),
    )
    return Response(content=body.encode("utf-8"), media_type="text/calendar; charset=utf-8")
