"""Global search across students and lessons."""

from __future__ import annotations

from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models import Lesson, Student, User

router = APIRouter(prefix="/search", tags=["search"])


class GlobalSearchStudentItem(BaseModel):
    id: int
    name: str
    subject: str
    grade: str
    school: str
    contact: str
    parent_contact: str
    parent_name: str = ""
    parent_email: str = ""
    parent_phone: str = ""
    notes: str


class GlobalSearchLessonItem(BaseModel):
    id: int
    student_id: int
    board_id: int | None = None
    lesson_date: date
    lesson_time: str
    duration_minutes: int
    payment_amount: float
    is_paid: bool
    is_conducted: bool
    status: str
    notes: str
    meeting_url: str
    student_name: str | None = None
    homework_id: int | None = None


class GlobalSearchOut(BaseModel):
    q: str
    students: list[GlobalSearchStudentItem]
    lessons: list[GlobalSearchLessonItem]


@router.get("", response_model=GlobalSearchOut)
def global_search(
    q: str = Query(min_length=1, max_length=100),
    limit_students: int = Query(10, ge=1, le=30),
    limit_lessons: int = Query(20, ge=1, le=50),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    term = (q or "").strip()

    students_rows = (
        db.query(Student)
        .filter(Student.tutor_id == user.id)
        .filter(Student.name.ilike(f"%{term}%"))
        .order_by(Student.name.asc())
        .limit(limit_students)
        .all()
    )

    lessons_rows = (
        db.query(Lesson, Student.name)
        .join(Student, Lesson.student_id == Student.id)
        .filter(Lesson.tutor_id == user.id)
        .filter(Student.name.ilike(f"%{term}%"))
        .order_by(Lesson.lesson_date.desc(), Lesson.lesson_time.desc())
        .limit(limit_lessons)
        .all()
    )

    students_out = [
        GlobalSearchStudentItem(
            id=s.id,
            name=s.name,
            subject=s.subject or "",
            grade=s.grade or "",
            school=s.school or "",
            contact=s.contact or "",
            parent_contact=s.parent_contact or "",
            parent_name=s.parent_name or "",
            parent_email=s.parent_email or "",
            parent_phone=s.parent_phone or "",
            notes=s.notes or "",
        )
        for s in students_rows
    ]

    lessons_out: list[GlobalSearchLessonItem] = []
    for l, student_name in lessons_rows:
        lessons_out.append(
            GlobalSearchLessonItem(
                id=l.id,
                student_id=l.student_id,
                board_id=l.board_id,
                lesson_date=l.lesson_date,
                lesson_time=l.lesson_time,
                duration_minutes=l.duration_minutes,
                payment_amount=l.payment_amount,
                is_paid=l.is_paid,
                is_conducted=l.is_conducted,
                status=l.status,
                notes=l.notes or "",
                meeting_url=l.meeting_url or "",
                student_name=student_name,
                homework_id=l.homework.id if getattr(l, "homework", None) else None,
            )
        )

    return GlobalSearchOut(q=term, students=students_out, lessons=lessons_out)

