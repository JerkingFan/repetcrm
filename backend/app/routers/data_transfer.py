"""Export/import students and lessons as CSV (Excel-compatible UTF-8 BOM)."""

from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, File, Query, UploadFile
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models import Lesson, Student, User
from app.schemas import ImportResultOut
from app.services.dashboard_cache import invalidate_dashboard
from app.services.audit_log import audit_event
from app.services.data_transfer import (
    export_lessons_csv,
    export_students_csv,
    import_lessons_csv,
    import_students_csv,
)

router = APIRouter(prefix="/data", tags=["data"])


@router.get("/export/students")
def export_students(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    students_count = db.query(Student).filter(Student.tutor_id == user.id).count()
    content = export_students_csv(db, user.id)
    audit_event(
        action="csv_export_students",
        entity_type="tutor",
        entity_id=user.id,
        actor_user_id=user.id,
        meta={"students_count": students_count},
    )
    return Response(
        content=content,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="students.csv"'},
    )


@router.get("/export/lessons")
def export_lessons(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    from_date: date | None = Query(None, alias="from"),
    to_date: date | None = Query(None, alias="to"),
):
    q = (
        db.query(Lesson)
        .filter(Lesson.tutor_id == user.id)
    )
    if from_date:
        q = q.filter(Lesson.lesson_date >= from_date)
    if to_date:
        q = q.filter(Lesson.lesson_date <= to_date)
    lessons_count = q.count()

    content = export_lessons_csv(db, user.id, from_date=from_date, to_date=to_date)
    audit_event(
        action="csv_export_lessons",
        entity_type="tutor",
        entity_id=user.id,
        actor_user_id=user.id,
        meta={"from_date": str(from_date) if from_date else None, "to_date": str(to_date) if to_date else None, "lessons_count": lessons_count},
    )
    return Response(
        content=content,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="lessons.csv"'},
    )


@router.post("/import/students", response_model=ImportResultOut)
async def import_students(
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    result = import_students_csv(db, user.id, file.file)
    invalidate_dashboard(user.id)
    return result


@router.post("/import/lessons", response_model=ImportResultOut)
async def import_lessons(
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    result = import_lessons_csv(db, user.id, file.file)
    invalidate_dashboard(user.id)
    return result
