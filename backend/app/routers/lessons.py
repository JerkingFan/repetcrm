from datetime import date
import secrets

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.dependencies import get_current_user
from app.models import User, Student, Lesson, ChecklistItem, Homework, Board
from app.schemas import (
    LessonCreate,
    LessonUpdate,
    LessonOut,
    ChecklistBulkCreate,
    LessonReportCreate,
    HomeworkPrefs,
    DashboardStats,
    HomeworkOut,
)
from app.services.homework_prefs import (
    apply_prefs_to_checklist,
    parse_homework_prefs,
    serialize_homework_prefs,
)
from app.services.homework_ai import generate_homework_ai
from app.services.ollama_client import OllamaError
from app.services.openrouter_client import OpenRouterError

router = APIRouter(tags=["lessons"])


def get_lesson_or_404(lesson_id: int, user: User, db: Session) -> Lesson:
    lesson = (
        db.query(Lesson)
        .options(
            joinedload(Lesson.student),
            joinedload(Lesson.checklist_items),
            joinedload(Lesson.homework),
        )
        .filter(Lesson.id == lesson_id, Lesson.tutor_id == user.id)
        .first()
    )
    if not lesson:
        raise HTTPException(status_code=404, detail="Lesson not found")
    return lesson


def lesson_to_out(lesson: Lesson) -> LessonOut:
    prefs_data = parse_homework_prefs(lesson.homework_prefs)
    return LessonOut(
        id=lesson.id,
        student_id=lesson.student_id,
        board_id=lesson.board_id,
        lesson_date=lesson.lesson_date,
        lesson_time=lesson.lesson_time or "10:00",
        duration_minutes=lesson.duration_minutes,
        payment_amount=lesson.payment_amount,
        is_paid=lesson.is_paid,
        is_conducted=bool(lesson.is_conducted),
        homework_prefs=HomeworkPrefs(**prefs_data),
        notes=lesson.notes,
        created_at=lesson.created_at,
        student_name=lesson.student.name if lesson.student else None,
        checklist_items=lesson.checklist_items,
        homework=lesson.homework,
    )


@router.get("/dashboard", response_model=DashboardStats)
def dashboard(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    today = date.today()
    month_start = today.replace(day=1)
    students_count = db.query(Student).filter(Student.tutor_id == user.id).count()
    lessons = db.query(Lesson).filter(
        Lesson.tutor_id == user.id,
        Lesson.lesson_date >= month_start,
    ).all()
    lessons_this_month = len(lessons)
    payments_this_month = sum(l.payment_amount for l in lessons if l.is_paid)
    all_lessons = db.query(Lesson).filter(Lesson.tutor_id == user.id, Lesson.is_paid == False).all()
    unpaid_total = sum(l.payment_amount for l in all_lessons)
    return DashboardStats(
        students_count=students_count,
        lessons_this_month=lessons_this_month,
        payments_this_month=payments_this_month,
        unpaid_total=unpaid_total,
    )


@router.get("/lessons", response_model=list[LessonOut])
def list_lessons(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    lessons = (
        db.query(Lesson)
        .options(joinedload(Lesson.student), joinedload(Lesson.checklist_items), joinedload(Lesson.homework))
        .filter(Lesson.tutor_id == user.id)
        .order_by(Lesson.lesson_date.desc())
        .all()
    )
    return [lesson_to_out(l) for l in lessons]


@router.post("/lessons", response_model=LessonOut, status_code=201)
def create_lesson(data: LessonCreate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    student = db.query(Student).filter(Student.id == data.student_id, Student.tutor_id == user.id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    # Auto-create a board for the lesson
    board = Board(owner_id=user.id, title=f"Доска: {student.name}", share_token=secrets.token_urlsafe(24))
    db.add(board)
    db.flush()
    lesson = Lesson(tutor_id=user.id, board_id=board.id, **data.model_dump())
    db.add(lesson)
    db.commit()
    db.refresh(lesson)
    lesson = get_lesson_or_404(lesson.id, user, db)
    return lesson_to_out(lesson)


@router.get("/lessons/{lesson_id}", response_model=LessonOut)
def get_lesson(lesson_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    lesson = get_lesson_or_404(lesson_id, user, db)
    return lesson_to_out(lesson)


@router.put("/lessons/{lesson_id}", response_model=LessonOut)
def update_lesson(
    lesson_id: int,
    data: LessonUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    lesson = get_lesson_or_404(lesson_id, user, db)
    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(lesson, k, v)
    db.commit()
    lesson = get_lesson_or_404(lesson_id, user, db)
    return lesson_to_out(lesson)


@router.delete("/lessons/{lesson_id}", status_code=204)
def delete_lesson(lesson_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    lesson = get_lesson_or_404(lesson_id, user, db)
    db.delete(lesson)
    db.commit()


@router.post("/lessons/{lesson_id}/checklist", response_model=LessonOut)
def save_checklist(
    lesson_id: int,
    data: ChecklistBulkCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    lesson = get_lesson_or_404(lesson_id, user, db)
    db.query(ChecklistItem).filter(ChecklistItem.lesson_id == lesson_id).delete()
    for item in data.items:
        db.add(ChecklistItem(lesson_id=lesson_id, **item.model_dump()))
    db.commit()
    lesson = get_lesson_or_404(lesson_id, user, db)
    return lesson_to_out(lesson)


@router.post("/lessons/{lesson_id}/lesson-report", response_model=LessonOut)
def save_lesson_report(
    lesson_id: int,
    data: LessonReportCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Темы + настройки ДЗ после проведённого занятия."""
    lesson = get_lesson_or_404(lesson_id, user, db)
    db.query(ChecklistItem).filter(ChecklistItem.lesson_id == lesson_id).delete()
    for item in data.items:
        db.add(ChecklistItem(lesson_id=lesson_id, **item.model_dump()))
    lesson.is_conducted = data.is_conducted
    lesson.homework_prefs = serialize_homework_prefs(data.prefs.model_dump())
    db.commit()
    lesson = get_lesson_or_404(lesson_id, user, db)
    return lesson_to_out(lesson)


@router.post("/lessons/{lesson_id}/generate-homework", response_model=HomeworkOut)
async def generate_lesson_homework(
    lesson_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    lesson = get_lesson_or_404(lesson_id, user, db)
    if not lesson.is_conducted:
        raise HTTPException(
            status_code=400,
            detail="Сначала отметьте занятие проведённым и заполните чек-лист",
        )
    if not lesson.checklist_items:
        raise HTTPException(status_code=400, detail="Добавьте хотя бы одну тему")
    prefs = parse_homework_prefs(lesson.homework_prefs)

    checklist = apply_prefs_to_checklist(
        [
            {
                "topic": i.topic,
                "work_type": i.work_type,
                "difficulty": i.difficulty,
                "understanding": i.understanding,
            }
            for i in lesson.checklist_items
        ],
        prefs,
    )
    from app.config import get_settings

    cfg = get_settings()
    try:
        html, source, hint = await generate_homework_ai(
            lesson.student.name,
            lesson.student.subject,
            checklist,
            lesson.student.grade,
            homework_prefs=prefs,
        )
    except (OllamaError, OpenRouterError) as e:
        raise HTTPException(status_code=503, detail=str(e))
    if lesson.homework:
        lesson.homework.homework_text = html
        hw = lesson.homework
    else:
        hw = Homework(lesson_id=lesson_id, homework_text=html)
        db.add(hw)
    db.commit()
    db.refresh(hw)
    return HomeworkOut(
        id=hw.id,
        lesson_id=hw.lesson_id,
        homework_text=hw.homework_text,
        created_at=hw.created_at,
        updated_at=hw.updated_at,
        student_name=lesson.student.name,
        lesson_date=lesson.lesson_date,
        generation_source=source,
        generation_hint=hint,
        configured_provider=cfg.homework_ai_provider,
        configured_model=cfg.openrouter_model,
    )
