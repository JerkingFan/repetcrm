from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.dependencies import get_current_user
from app.models import User, Student, Lesson
from app.schemas import (
    StudentCreate,
    StudentUpdate,
    StudentOut,
    StudentListPage,
    StudentWithLessons,
    LessonOut,
    StudentBoundariesOut,
    BoundaryApplyIn,
    BoundaryMessageOut,
)
from app.services.boundaries import (
    decide_boundary_mode,
    apply_boundary_mode,
    render_boundary_message,
    BOUNDARY_RULES,
    MODE_SEVERITY,
)
from app.services.dashboard_cache import invalidate_dashboard
from app.models import StudentBoundaryMode

router = APIRouter(prefix="/students", tags=["students"])


def _parse_mode(raw: str | None) -> StudentBoundaryMode:
    value = (raw or StudentBoundaryMode.normal.value).strip().lower()
    try:
        return StudentBoundaryMode(value)
    except ValueError:
        return StudentBoundaryMode.normal


def lesson_to_out(lesson) -> LessonOut:
    return LessonOut(
        id=lesson.id,
        student_id=lesson.student_id,
        lesson_date=lesson.lesson_date,
        lesson_time=getattr(lesson, "lesson_time", None) or "10:00",
        duration_minutes=lesson.duration_minutes,
        payment_amount=lesson.payment_amount,
        is_paid=lesson.is_paid,
        is_conducted=bool(getattr(lesson, "is_conducted", False)),
        status=getattr(lesson, "status", "scheduled") or "scheduled",
        late_minutes=int(getattr(lesson, "late_minutes", 0) or 0),
        rescheduled_from_lesson_id=getattr(lesson, "rescheduled_from_lesson_id", None),
        notes=lesson.notes,
        created_at=lesson.created_at,
        student_name=lesson.student.name if lesson.student else None,
        checklist_items=lesson.checklist_items,
        homework=lesson.homework,
    )

@router.get("", response_model=StudentListPage)
def list_students(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    q: str | None = Query(None, max_length=100, description="Поиск по имени"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    query = db.query(Student).filter(Student.tutor_id == user.id)
    if q and q.strip():
        query = query.filter(Student.name.ilike(f"%{q.strip()}%"))
    total = query.count()
    offset = (page - 1) * page_size
    rows = query.order_by(Student.name).offset(offset).limit(page_size).all()
    return StudentListPage(
        items=rows,
        total=total,
        page=page,
        page_size=page_size,
        has_more=offset + len(rows) < total,
    )


@router.post("", response_model=StudentOut, status_code=201)
def create_student(data: StudentCreate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    student = Student(tutor_id=user.id, **data.model_dump())
    db.add(student)
    db.commit()
    db.refresh(student)
    invalidate_dashboard(user.id)
    return student


@router.get("/{student_id}", response_model=StudentWithLessons)
def get_student(student_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    student = (
        db.query(Student)
        .options(
            joinedload(Student.lessons).joinedload(Lesson.checklist_items),
            joinedload(Student.lessons).joinedload(Lesson.homework),
        )
        .filter(Student.id == student_id, Student.tutor_id == user.id)
        .first()
    )
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    lessons_out = [lesson_to_out(l) for l in sorted(student.lessons, key=lambda x: x.lesson_date, reverse=True)]
    return StudentWithLessons(
        id=student.id,
        name=student.name,
        subject=student.subject,
        contact=student.contact,
        created_at=student.created_at,
        grade=student.grade,
        school=student.school,
        parent_contact=student.parent_contact,
        notes=student.notes,
        boundary_mode=getattr(student, "boundary_mode", "normal"),
        boundary_reason=getattr(student, "boundary_reason", ""),
        boundary_updated_at=getattr(student, "boundary_updated_at", None),
        lessons=lessons_out,
    )


@router.get("/{student_id}/boundaries", response_model=StudentBoundariesOut)
def get_student_boundaries(
    student_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    student = db.query(Student).filter(Student.id == student_id, Student.tutor_id == user.id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    decision = decide_boundary_mode(db, tutor_id=user.id, student_id=student_id)
    current_mode = _parse_mode(getattr(student, "boundary_mode", "normal"))
    suggested_mode = decision.mode
    notification_message: str | None = None
    if MODE_SEVERITY[suggested_mode] > MODE_SEVERITY[current_mode]:
        notification_message = render_boundary_message(
            student.name, suggested_mode, decision.reason, escalated=True
        )
    return StudentBoundariesOut(
        student_id=student.id,
        student_name=student.name,
        boundary_mode=current_mode.value,
        boundary_reason=getattr(student, "boundary_reason", ""),
        boundary_updated_at=getattr(student, "boundary_updated_at", None),
        suggested_mode=suggested_mode.value,
        suggested_reason=decision.reason,
        signals=decision.signals,
        rules=BOUNDARY_RULES[suggested_mode],
        notification_message=notification_message,
    )


@router.get("/{student_id}/boundaries/message", response_model=BoundaryMessageOut)
def get_boundary_message(
    student_id: int,
    mode: str | None = Query(None, description="yellow|orange|red|normal; по умолчанию — suggested"),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    student = db.query(Student).filter(Student.id == student_id, Student.tutor_id == user.id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    decision = decide_boundary_mode(db, tutor_id=user.id, student_id=student_id)
    if mode:
        if mode.strip().lower() not in {m.value for m in StudentBoundaryMode}:
            raise HTTPException(status_code=400, detail="Invalid mode")
        target_mode = StudentBoundaryMode(mode.strip().lower())
        reason = decision.reason
    else:
        target_mode = decision.mode
        reason = decision.reason
    message = render_boundary_message(student.name, target_mode, reason, escalated=True)
    if not message and target_mode == StudentBoundaryMode.normal:
        message = render_boundary_message(student.name, target_mode, reason, escalated=False)
    return BoundaryMessageOut(
        student_id=student.id,
        student_name=student.name,
        mode=target_mode.value,
        reason=reason,
        rules=BOUNDARY_RULES[target_mode],
        message=message,
    )


@router.post("/{student_id}/boundaries/apply", response_model=StudentOut)
def apply_student_boundaries(
    student_id: int,
    data: BoundaryApplyIn,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    mode_raw = data.mode.strip().lower()
    reason = data.reason.strip()
    if mode_raw not in {m.value for m in StudentBoundaryMode}:
        raise HTTPException(status_code=400, detail="Invalid mode")
    mode = StudentBoundaryMode(mode_raw)
    if not reason:
        decision = decide_boundary_mode(db, tutor_id=user.id, student_id=student_id)
        reason = decision.reason
    try:
        student = apply_boundary_mode(db, tutor_id=user.id, student_id=student_id, mode=mode, reason=reason)
    except ValueError:
        raise HTTPException(status_code=404, detail="Student not found")
    return student


@router.put("/{student_id}", response_model=StudentOut)
def update_student(
    student_id: int,
    data: StudentUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    student = db.query(Student).filter(Student.id == student_id, Student.tutor_id == user.id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(student, k, v)
    db.commit()
    db.refresh(student)
    return student


@router.delete("/{student_id}", status_code=204)
def delete_student(student_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    student = db.query(Student).filter(Student.id == student_id, Student.tutor_id == user.id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    db.delete(student)
    db.commit()
    invalidate_dashboard(user.id)
