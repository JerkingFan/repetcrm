import calendar
import logging
import secrets
from datetime import date, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import and_, case, func
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.dependencies import get_current_user
from app.models import User, Student, Lesson, ChecklistItem, Homework, Board, LessonStatus, LessonSeries
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
    DashboardExtended,
    HomeworkOut,
    HomeworkJobOut,
    HomeworkJobStartOut,
    LessonCreateResult,
    LessonSeriesOut,
    LessonRecurrenceIn,
    QuickConductOut,
    LessonVoiceBriefIn,
    LessonVoiceBriefOut,
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
from app.services.dashboard_extended import build_extended_dashboard
from app.services.job_queue import job_queue, ARQ_TASK_GENERATE_HOMEWORK
from app.services.job_tasks import run_generate_homework
from app.services.pdf import invalidate_homework_pdf
from app.services.lesson_recurrence import expand_series
from app.services.manual_trial import apply_manual_trial_lesson
from app.services.package_billing import try_auto_pay_lesson
from app.services.student_lifecycle import touch_student_lesson_dates
from app.services.trial_funnel_service import get_trial_followup
from app.services.portal_student import default_homework_due_date

logger = logging.getLogger(__name__)

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
        meeting_url=getattr(lesson, "meeting_url", "") or "",
        created_at=lesson.created_at,
        student_name=lesson.student.name if lesson.student else None,
        series_id=getattr(lesson, "series_id", None),
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
        meeting_url=getattr(lesson, "meeting_url", "") or "",
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
        # Default: from start of previous month through ~2 months ahead
        # (recurring series often spill into next month)
        start = (today.replace(day=1) - timedelta(days=1)).replace(day=1)
        end = today + timedelta(days=62)
        return start, end
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


@router.get("/dashboard/extended", response_model=DashboardExtended)
def dashboard_extended(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return build_extended_dashboard(db, user.id, tutor_name=user.name or "")


@router.get("/lessons", response_model=list[LessonListItem])
def list_lessons(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    from_date: date | None = Query(None, alias="from", description="Начало периода (YYYY-MM-DD)"),
    to_date: date | None = Query(None, alias="to", description="Конец периода (YYYY-MM-DD)"),
    student_id: int | None = Query(None, description="Фильтр по ученику"),
    is_paid: bool | None = Query(None, description="Оплачено / не оплачено"),
    is_conducted: bool | None = Query(None, description="Проведено / не проведено"),
    status: str | None = Query(None, description="scheduled|completed|cancelled|no_show|rescheduled"),
):
    range_start, range_end = _resolve_lesson_range(from_date, to_date)
    q = (
        db.query(Lesson, Student.name, Homework.id)
        .join(Student, Lesson.student_id == Student.id)
        .outerjoin(Homework, Homework.lesson_id == Lesson.id)
        .filter(
            Lesson.tutor_id == user.id,
            Lesson.lesson_date >= range_start,
            Lesson.lesson_date <= range_end,
        )
    )
    if student_id is not None:
        q = q.filter(Lesson.student_id == student_id)
    if is_paid is not None:
        q = q.filter(Lesson.is_paid.is_(is_paid))
    if is_conducted is not None:
        q = q.filter(Lesson.is_conducted.is_(is_conducted))
    if status is not None:
        q = q.filter(Lesson.status == status.strip().lower())
    rows = q.order_by(Lesson.lesson_date.desc(), Lesson.lesson_time.desc()).all()
    return [
        lesson_list_item(lesson, student_name=student_name, homework_id=homework_id)
        for lesson, student_name, homework_id in rows
    ]


@router.post("/lessons", response_model=LessonCreateResult, status_code=201)
def create_lesson(data: LessonCreate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    student = db.query(Student).filter(Student.id == data.student_id, Student.tutor_id == user.id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    if data.is_trial and data.recurrence:
        raise HTTPException(
            status_code=400,
            detail="Пробный урок нельзя создать как повторяющуюся серию",
        )

    series_out: LessonSeriesOut | None = None
    payload = data.model_dump(exclude={"recurrence", "is_trial"})
    recurrence: LessonRecurrenceIn | None = data.recurrence

    if data.is_trial:
        apply_manual_trial_lesson(
            db,
            tutor_id=user.id,
            student=student,
            lesson_date=data.lesson_date,
            lesson_time=data.lesson_time,
        )

    if recurrence:
        if data.lesson_date.weekday() != recurrence.weekday:
            raise HTTPException(
                status_code=400,
                detail="lesson_date weekday must match recurrence.weekday",
            )
        series = LessonSeries(
            tutor_id=user.id,
            student_id=data.student_id,
            weekday=recurrence.weekday,
            lesson_time=data.lesson_time,
            duration_minutes=data.duration_minutes,
            payment_amount=data.payment_amount,
            notes=data.notes or "",
            starts_on=data.lesson_date,
            until_date=recurrence.until_date,
            weeks_ahead=recurrence.weeks_ahead,
        )
        db.add(series)
        db.flush()
        created_n = expand_series(db, series)
        db.flush()
        first_lesson = (
            db.query(Lesson)
            .filter(Lesson.series_id == series.id)
            .order_by(Lesson.lesson_date.asc())
            .first()
        )
        if not first_lesson:
            raise HTTPException(status_code=500, detail="Failed to create recurring lessons")
        db.commit()
        invalidate_dashboard(user.id)
        lesson = get_lesson_or_404(first_lesson.id, user, db)
        series_out = LessonSeriesOut(
            id=series.id,
            student_id=series.student_id,
            weekday=series.weekday,
            lesson_time=series.lesson_time,
            duration_minutes=series.duration_minutes,
            payment_amount=series.payment_amount,
            starts_on=series.starts_on,
            until_date=series.until_date,
            weeks_ahead=series.weeks_ahead,
            is_active=series.is_active,
            lessons_created=created_n,
        )
        return LessonCreateResult(lesson=lesson_to_out(lesson), series=series_out)

    board = Board(
        owner_id=user.id,
        title=f"Доска: {student.name}",
        share_token=secrets.token_urlsafe(24),
        share_writable=False,
    )
    db.add(board)
    db.flush()
    lesson = Lesson(tutor_id=user.id, board_id=board.id, **payload)
    db.add(lesson)
    db.commit()
    invalidate_dashboard(user.id)
    lesson = get_lesson_or_404(lesson.id, user, db)
    return LessonCreateResult(lesson=lesson_to_out(lesson), series=None)


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
    if updates.get("is_paid") is True and not lesson.paid_at:
        lesson.paid_at = datetime.utcnow()
        if not lesson.payment_source:
            lesson.payment_source = "manual"
    if updates.get("is_paid") is False:
        lesson.paid_at = None
        lesson.payment_source = None
    boundary_sync = _maybe_sync_boundaries(db, user, lesson.student_id, set(updates.keys()))
    if lesson.is_conducted and not lesson.is_paid:
        try_auto_pay_lesson(db, lesson)
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
    if lesson.is_conducted:
        touch_student_lesson_dates(db, lesson.student_id, lesson.lesson_date)
    if lesson.is_conducted and not lesson.is_paid:
        try_auto_pay_lesson(db, lesson)
    db.commit()
    lesson = get_lesson_or_404(lesson_id, user, db)
    return lesson_to_out(lesson)


@router.post("/lessons/{lesson_id}/quick-conduct", response_model=QuickConductOut)
def quick_conduct_lesson(
    lesson_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Mark trial lesson as conducted without full checklist (dashboard shortcut)."""
    lesson = get_lesson_or_404(lesson_id, user, db)
    if lesson.is_conducted:
        raise HTTPException(status_code=400, detail="Lesson already conducted")
    lesson.is_conducted = True
    lesson.status = LessonStatus.completed.value
    touch_student_lesson_dates(db, lesson.student_id, lesson.lesson_date)
    if not lesson.is_paid:
        try_auto_pay_lesson(db, lesson)
    db.commit()
    invalidate_dashboard(user.id)
    student = db.query(Student).filter(Student.id == lesson.student_id).first()
    followup = get_trial_followup(db, student, user.name or "") if student else None
    return QuickConductOut(
        lesson_id=lesson.id,
        is_conducted=True,
        trial_followup=followup if followup and followup.show else None,
    )


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
        logger.warning(
            "homework AI unavailable lesson_id=%s: %s",
            lesson_id,
            e,
            extra={"lesson_id": lesson_id},
        )
        raise HTTPException(
            status_code=503,
            detail="Сервис генерации ДЗ временно недоступен. Попробуйте позже.",
        )
    if lesson.homework:
        lesson.homework.homework_text = html
        hw = lesson.homework
    else:
        hw = Homework(lesson_id=lesson_id, homework_text=html)
        db.add(hw)
    if not hw.due_date:
        hw.due_date = default_homework_due_date(db, lesson)
    db.commit()
    db.refresh(hw)
    invalidate_homework_pdf(hw.id)
    return HomeworkOut(
        id=hw.id,
        lesson_id=hw.lesson_id,
        homework_text=hw.homework_text,
        due_date=getattr(hw, "due_date", None),
        created_at=hw.created_at,
        updated_at=hw.updated_at,
        student_name=lesson.student.name,
        lesson_date=lesson.lesson_date,
        generation_source=source,
        generation_hint=hint,
        configured_provider=cfg.homework_ai_provider,
        configured_model=cfg.openrouter_model,
    )


@router.post("/lessons/{lesson_id}/voice-brief", response_model=LessonVoiceBriefOut)
async def lesson_voice_brief(
    lesson_id: int,
    data: LessonVoiceBriefIn,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Save spoken brief into homework prefs and optionally start AI generation."""
    lesson = get_lesson_or_404(lesson_id, user, db)
    brief = (data.brief or "").strip()[:2000]
    if len(brief) < 3:
        raise HTTPException(status_code=400, detail="Слишком короткий голос/текст")

    prefs = parse_homework_prefs(lesson.homework_prefs)
    prefs["special_notes"] = brief
    import re

    m = re.search(r"(\d+)\s*(задач|упражнен|пример)", brief.lower())
    if m:
        n = int(m.group(1))
        prefs["volume"] = "minimal" if n <= 3 else ("extended" if n >= 8 else "standard")
    lesson.homework_prefs = serialize_homework_prefs(prefs)
    db.commit()

    job_id = None
    status = "saved"
    if data.start_generation:
        if not lesson.is_conducted:
            raise HTTPException(
                status_code=400,
                detail="Сначала отметьте занятие проведённым",
            )
        if not lesson.checklist_items:
            # seed one topic from brief
            topic = brief.split(",")[0].strip()[:200] or "Практика"
            db.add(
                ChecklistItem(
                    lesson_id=lesson.id,
                    topic=topic,
                    work_type="practice",
                    difficulty="medium",
                    understanding=3,
                )
            )
            db.commit()
        job = await job_queue.enqueue_unique(
            owner_user_id=user.id,
            key_type="lesson",
            key_value=lesson_id,
            job_type="generate_homework",
            arq_task=ARQ_TASK_GENERATE_HOMEWORK,
            arq_args=(lesson_id, user.id),
            inprocess_runner=lambda: run_generate_homework(lesson_id, user.id),
        )
        job_id = job.id
        status = job.status

    return LessonVoiceBriefOut(brief=brief, job_id=job_id, status=status)


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

    job = await job_queue.enqueue_unique(
        owner_user_id=user.id,
        key_type="lesson",
        key_value=lesson_id,
        job_type="generate_homework",
        arq_task=ARQ_TASK_GENERATE_HOMEWORK,
        arq_args=(lesson_id, user.id),
        inprocess_runner=lambda: run_generate_homework(lesson_id, user.id),
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
