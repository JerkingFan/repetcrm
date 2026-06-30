import asyncio
from datetime import date, datetime, timedelta
import calendar
import secrets

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import and_, case, func
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.dependencies import get_current_user
from app.models import User, Student, Lesson, ChecklistItem, Homework, Board, LessonStatus
from app.schemas import (
    LessonCreate,
    LessonUpdate,
    LessonOut,
    LessonListItem,
    LessonWithBoundarySync,
    BoundarySyncOut,
    ChecklistBulkCreate,
    LessonReportCreate,
    HomeworkPrefs,
    DashboardStats,
    HomeworkOut,
    HomeworkJobOut,
    HomeworkJobStartOut,
)
from app.services.homework_prefs import (
    apply_prefs_to_checklist,
    parse_homework_prefs,
    serialize_homework_prefs,
)
from app.services.homework_ai import generate_homework_ai
from app.services.ollama_client import OllamaError
from app.services.openrouter_client import OpenRouterError
from app.services.boundaries import sync_student_boundaries
from app.services.dashboard_cache import (
    get_cached_dashboard,
    invalidate_dashboard,
    set_cached_dashboard,
)
from app.services.job_queue import job_queue
from app.services.smart_homework import generate_smart_homework_latex
from app.services.pdf import invalidate_homework_pdf

router = APIRouter(tags=["lessons"])

BOUNDARY_TRIGGER_FIELDS = frozenset({"status", "late_minutes", "is_paid", "lesson_date"})


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
        status=getattr(lesson, "status", "scheduled") or "scheduled",
        late_minutes=int(getattr(lesson, "late_minutes", 0) or 0),
        rescheduled_from_lesson_id=getattr(lesson, "rescheduled_from_lesson_id", None),
        homework_prefs=HomeworkPrefs(**prefs_data),
        notes=lesson.notes,
        created_at=lesson.created_at,
        student_name=lesson.student.name if lesson.student else None,
        checklist_items=lesson.checklist_items,
        homework=lesson.homework,
    )


def lesson_list_item(
    lesson: Lesson,
    *,
    student_name: str | None = None,
    homework_id: int | None = None,
) -> LessonListItem:
    return LessonListItem(
        id=lesson.id,
        student_id=lesson.student_id,
        board_id=lesson.board_id,
        lesson_date=lesson.lesson_date,
        lesson_time=lesson.lesson_time or "10:00",
        duration_minutes=lesson.duration_minutes,
        payment_amount=lesson.payment_amount,
        is_paid=lesson.is_paid,
        is_conducted=bool(lesson.is_conducted),
        status=getattr(lesson, "status", "scheduled") or "scheduled",
        notes=lesson.notes or "",
        student_name=student_name or (lesson.student.name if lesson.student else None),
        homework_id=homework_id,
    )


def _month_bounds(year: int, month: int) -> tuple[date, date]:
    last_day = calendar.monthrange(year, month)[1]
    return date(year, month, 1), date(year, month, last_day)


def _resolve_lesson_range(
    from_date: date | None,
    to_date: date | None,
) -> tuple[date, date]:
    today = date.today()
    if from_date is None and to_date is None:
        return _month_bounds(today.year, today.month)
    if from_date is None:
        from_date = to_date.replace(day=1) if to_date else today.replace(day=1)
    if to_date is None:
        to_date = from_date + timedelta(days=31)
        to_date = to_date.replace(day=calendar.monthrange(to_date.year, to_date.month)[1])
    if from_date > to_date:
        from_date, to_date = to_date, from_date
    return from_date, to_date


def _boundary_sync_out(result) -> BoundarySyncOut | None:
    if not result.mode_changed:
        return None
    return BoundarySyncOut(
        previous_mode=result.previous_mode.value,
        new_mode=result.new_mode.value,
        mode_changed=result.mode_changed,
        escalated=result.escalated,
        reason=result.reason,
        message=result.message,
    )


def _maybe_sync_boundaries(
    db: Session, user: User, student_id: int, changed_fields: set[str]
) -> BoundarySyncOut | None:
    if not changed_fields & BOUNDARY_TRIGGER_FIELDS:
        return None
    result = sync_student_boundaries(db, tutor_id=user.id, student_id=student_id)
    return _boundary_sync_out(result)


@router.get("/dashboard", response_model=DashboardStats)
def dashboard(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    cached = get_cached_dashboard(user.id)
    if cached is not None:
        return DashboardStats(**cached)

    today = date.today()
    month_start = today.replace(day=1)
    tutor_id = user.id

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

    stats = DashboardStats(
        students_count=int(students_count),
        lessons_this_month=int(lesson_stats.lessons_this_month or 0),
        payments_this_month=float(lesson_stats.payments_this_month or 0),
        unpaid_total=float(lesson_stats.unpaid_total or 0),
    )
    set_cached_dashboard(user.id, stats.model_dump())
    return stats


@router.get("/lessons", response_model=list[LessonListItem])
def list_lessons(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    from_date: date | None = Query(None, alias="from", description="Начало периода (YYYY-MM-DD)"),
    to_date: date | None = Query(None, alias="to", description="Конец периода (YYYY-MM-DD)"),
):
    range_start, range_end = _resolve_lesson_range(from_date, to_date)
    rows = (
        db.query(Lesson, Student.name, Homework.id)
        .join(Student, Lesson.student_id == Student.id)
        .outerjoin(Homework, Homework.lesson_id == Lesson.id)
        .filter(
            Lesson.tutor_id == user.id,
            Lesson.lesson_date >= range_start,
            Lesson.lesson_date <= range_end,
        )
        .order_by(Lesson.lesson_date.desc(), Lesson.lesson_time.desc())
        .all()
    )
    return [
        lesson_list_item(lesson, student_name=student_name, homework_id=homework_id)
        for lesson, student_name, homework_id in rows
    ]


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
    invalidate_dashboard(user.id)
    lesson = get_lesson_or_404(lesson.id, user, db)
    return lesson_to_out(lesson)


@router.get("/lessons/{lesson_id}", response_model=LessonOut)
def get_lesson(lesson_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    lesson = get_lesson_or_404(lesson_id, user, db)
    return lesson_to_out(lesson)


@router.put("/lessons/{lesson_id}", response_model=LessonWithBoundarySync)
def update_lesson(
    lesson_id: int,
    data: LessonUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    lesson = get_lesson_or_404(lesson_id, user, db)
    updates = data.model_dump(exclude_unset=True)
    if "status" in updates and updates["status"] != lesson.status:
        lesson.status_changed_at = datetime.utcnow()
        if updates["status"] == LessonStatus.completed.value:
            lesson.is_conducted = True
    for k, v in updates.items():
        setattr(lesson, k, v)
    boundary_sync = _maybe_sync_boundaries(db, user, lesson.student_id, set(updates.keys()))
    db.commit()
    invalidate_dashboard(user.id)
    lesson = get_lesson_or_404(lesson_id, user, db)
    return LessonWithBoundarySync(lesson=lesson_to_out(lesson), boundary_sync=boundary_sync)


@router.delete("/lessons/{lesson_id}", status_code=204)
def delete_lesson(lesson_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    lesson = get_lesson_or_404(lesson_id, user, db)
    db.delete(lesson)
    db.commit()
    invalidate_dashboard(user.id)


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
    invalidate_homework_pdf(hw.id)
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


@router.post("/lessons/{lesson_id}/generate-homework-job", response_model=HomeworkJobStartOut, status_code=202)
async def start_generate_homework_job(
    lesson_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    MVP: запускает генерацию в фоне и возвращает job_id для polling.
    """
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

    async def _run():
        from app.config import get_settings
        from app.database import SessionLocal

        cfg = get_settings()
        # Hard cap to avoid tying up workers forever
        openrouter_cap_sec = 60.0

        # Generate content (LaTeX)
        try:
            html, source, hint = await asyncio.wait_for(
                generate_homework_ai(
                    lesson.student.name,
                    lesson.student.subject,
                    checklist,
                    lesson.student.grade,
                    homework_prefs=prefs,
                ),
                timeout=openrouter_cap_sec if cfg.homework_ai_provider in ("openrouter", "auto") else 900.0,
            )
        except Exception as e:
            # Fast fallback to smart (always works)
            html = generate_smart_homework_latex(
                lesson.student.name,
                lesson.student.subject,
                checklist,
                lesson.student.grade or "",
                homework_prefs=prefs,
            )
            source = "smart_fallback"
            hint = f"AI timeout/error: {e}. Использован шаблон."

        # Save homework in DB (new session)
        db2 = SessionLocal()
        try:
            l2 = get_lesson_or_404(lesson_id, user, db2)
            if l2.homework:
                l2.homework.homework_text = html
                hw2 = l2.homework
            else:
                hw2 = Homework(lesson_id=lesson_id, homework_text=html)
                db2.add(hw2)
            db2.commit()
            db2.refresh(hw2)
            invalidate_homework_pdf(hw2.id)
            return {
                "homework_id": hw2.id,
                "generation_source": source,
                "generation_hint": hint,
                "configured_provider": cfg.homework_ai_provider,
                "configured_model": cfg.openrouter_model,
            }
        finally:
            db2.close()

    job = await job_queue.enqueue_unique(
        owner_user_id=user.id,
        key_type="lesson",
        key_value=lesson_id,
        job_type="generate_homework",
        coro_factory=_run,
    )
    return HomeworkJobStartOut(job_id=job.id, status=job.status)


@router.get("/jobs/{job_id}", response_model=HomeworkJobOut)
async def get_job(job_id: str, user: User = Depends(get_current_user)):
    job = await job_queue.get(job_id)
    if not job or job.owner_user_id != user.id:
        raise HTTPException(status_code=404, detail="Job not found")
    return HomeworkJobOut(
        job_id=job.id,
        status=job.status,
        job_type=job.type,
        lesson_id=job.lesson_id,
        homework_id=job.homework_id,
        created_at_ms=job.created_at_ms,
        updated_at_ms=job.updated_at_ms,
        result=job.result,
        error=job.error,
    )
