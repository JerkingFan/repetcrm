"""Student cabinet: schedule, homework, submissions (portal auth)."""

from __future__ import annotations

import os
import uuid
from datetime import date, timedelta

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, Request, Response, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session, joinedload

from app.auth import create_portal_session_token
from app.config import get_settings
from app.database import get_db
from app.models import Homework, HomeworkSubmission, Lesson, LessonStatus, Student, User
from app.portal_cookies import clear_portal_cookie, read_portal_token, set_portal_cookie
from app.portal_dependencies import get_current_student
from app.schemas import (
    HomeworkSubmissionOut,
    PortalHomeworkDetailOut,
    PortalHomeworkOut,
    PortalLessonOut,
    PortalLoginIn,
    PortalStudentOut,
    PortalPaymentIntentIn,
    PaymentIntentOut,
)
from app.services.payment_service import create_payment_intent
from app.services.ics_calendar import build_ics
from app.services.homework_output import homework_content_to_html, homework_plain_preview
from app.services.homework_submission_ai import mark_submission_pending_ai, schedule_ai_review
from app.services.portal_token import student_by_portal_token
from app.services.auth_rate_limit import get_register_limiter

router = APIRouter(prefix="/portal", tags=["portal"])

_PORTAL_LOGIN_LIMIT = 20
_PORTAL_LOGIN_WINDOW_SEC = 300


def _client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for", "")
    if forwarded:
        return forwarded.split(",")[0].strip() or "unknown"
    if request.client:
        return request.client.host
    return "unknown"

_ALLOWED_MIME = {
    "application/pdf",
    "image/jpeg",
    "image/png",
    "image/webp",
    "image/heic",
    "image/heif",
}


def _preview(text: str) -> tuple[str, int]:
    return homework_plain_preview(text, max_len=140)


@router.post("/session", response_model=PortalStudentOut)
def portal_login(
    data: PortalLoginIn,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
):
    ip = _client_ip(request)
    limiter = get_register_limiter(_PORTAL_LOGIN_LIMIT, _PORTAL_LOGIN_WINDOW_SEC)
    rate_key = f"portal:{ip}"
    if limiter.is_blocked(rate_key):
        raise HTTPException(
            status_code=429,
            detail="Too many login attempts. Try again later.",
            headers={"Retry-After": str(limiter.retry_after_sec(rate_key))},
        )
    limiter.record(rate_key)

    student = student_by_portal_token(db, data.portal_token)
    if not student:
        raise HTTPException(status_code=400, detail="Invalid portal link")
    tutor = db.query(User).filter(User.id == student.tutor_id).first()
    session = create_portal_session_token(student.id)
    set_portal_cookie(response, session)
    return PortalStudentOut(
        id=student.id,
        name=student.name,
        subject=student.subject or "",
        grade=student.grade or "",
        balance=float(student.balance or 0),
        tutor_name=tutor.name if tutor else "",
    )


@router.post("/logout")
def portal_logout(response: Response):
    clear_portal_cookie(response)
    return {"ok": True}


@router.get("/me", response_model=PortalStudentOut)
def portal_me(student: Student = Depends(get_current_student), db: Session = Depends(get_db)):
    tutor = db.query(User).filter(User.id == student.tutor_id).first()
    return PortalStudentOut(
        id=student.id,
        name=student.name,
        subject=student.subject or "",
        grade=student.grade or "",
        balance=float(student.balance or 0),
        tutor_name=tutor.name if tutor else "",
    )


@router.get("/lessons", response_model=list[PortalLessonOut])
def portal_lessons(
    student: Student = Depends(get_current_student),
    db: Session = Depends(get_db),
    from_date: date | None = Query(None, alias="from"),
    to_date: date | None = Query(None, alias="to"),
):
    today = date.today()
    start = from_date or today
    end = to_date or (today + timedelta(days=60))
    rows = (
        db.query(Lesson)
        .filter(
            Lesson.student_id == student.id,
            Lesson.lesson_date >= start,
            Lesson.lesson_date <= end,
            Lesson.status != LessonStatus.cancelled.value,
        )
        .order_by(Lesson.lesson_date.asc(), Lesson.lesson_time.asc())
        .all()
    )
    return [
        PortalLessonOut(
            id=l.id,
            lesson_date=l.lesson_date,
            lesson_time=l.lesson_time or "10:00",
            duration_minutes=l.duration_minutes,
            status=l.status or "scheduled",
            is_conducted=bool(l.is_conducted),
            notes=l.notes or "",
        )
        for l in rows
    ]


@router.get("/homework", response_model=list[PortalHomeworkOut])
def portal_homework_list(student: Student = Depends(get_current_student), db: Session = Depends(get_db)):
    rows = (
        db.query(Homework, Lesson.lesson_date)
        .join(Lesson, Homework.lesson_id == Lesson.id)
        .filter(Lesson.student_id == student.id)
        .order_by(Lesson.lesson_date.desc())
        .all()
    )
    hw_ids = [hw.id for hw, _ in rows]
    submitted = set()
    status_by_hw: dict[int, str] = {}
    if hw_ids:
        subs = (
            db.query(HomeworkSubmission)
            .filter(
                HomeworkSubmission.homework_id.in_(hw_ids),
                HomeworkSubmission.student_id == student.id,
            )
            .order_by(HomeworkSubmission.submitted_at.desc())
            .all()
        )
        for sub in subs:
            submitted.add(sub.homework_id)
            if sub.homework_id not in status_by_hw:
                status_by_hw[sub.homework_id] = sub.status or "submitted"
    out: list[PortalHomeworkOut] = []
    for hw, lesson_date in rows:
        preview, tasks_count = _preview(hw.homework_text)
        out.append(
            PortalHomeworkOut(
                id=hw.id,
                lesson_id=hw.lesson_id,
                lesson_date=lesson_date,
                preview=preview,
                tasks_count=tasks_count,
                has_submission=hw.id in submitted,
                submission_status=status_by_hw.get(hw.id, "not_submitted"),
                updated_at=hw.updated_at,
            )
        )
    return out


@router.get("/homework/{homework_id}", response_model=PortalHomeworkDetailOut)
def portal_homework_detail(
    homework_id: int,
    student: Student = Depends(get_current_student),
    db: Session = Depends(get_db),
):
    row = (
        db.query(Homework, Lesson)
        .join(Lesson, Homework.lesson_id == Lesson.id)
        .filter(Homework.id == homework_id, Lesson.student_id == student.id)
        .first()
    )
    if not row:
        raise HTTPException(status_code=404, detail="Homework not found")
    hw, lesson = row
    subs = (
        db.query(HomeworkSubmission)
        .filter(
            HomeworkSubmission.homework_id == homework_id,
            HomeworkSubmission.student_id == student.id,
        )
        .order_by(HomeworkSubmission.submitted_at.desc())
        .all()
    )
    return PortalHomeworkDetailOut(
        id=hw.id,
        lesson_id=hw.lesson_id,
        lesson_date=lesson.lesson_date,
        homework_text=hw.homework_text,
        preview_html=homework_content_to_html(hw.homework_text, render_math_images=True),
        has_submission=len(subs) > 0,
        submissions=[HomeworkSubmissionOut.model_validate(s) for s in subs],
    )


@router.post("/homework/{homework_id}/submit", response_model=HomeworkSubmissionOut)
async def portal_submit_homework(
    homework_id: int,
    student: Student = Depends(get_current_student),
    db: Session = Depends(get_db),
    file: UploadFile = File(...),
    comment: str = Form(""),
):
    cfg = get_settings()
    row = (
        db.query(Homework, Lesson)
        .join(Lesson, Homework.lesson_id == Lesson.id)
        .filter(Homework.id == homework_id, Lesson.student_id == student.id)
        .first()
    )
    if not row:
        raise HTTPException(status_code=404, detail="Homework not found")

    content = await file.read()
    if len(content) > cfg.homework_submission_max_bytes:
        raise HTTPException(status_code=413, detail="File too large")
    mime = (file.content_type or "").split(";")[0].strip().lower()
    if mime not in _ALLOWED_MIME:
        raise HTTPException(status_code=400, detail="Allowed: PDF, JPEG, PNG, WebP")

    sub_dir = os.path.join(cfg.media_dir, "submissions", str(homework_id))
    os.makedirs(sub_dir, exist_ok=True)
    ext = os.path.splitext(file.filename or "upload")[1] or ".bin"
    fname = f"{uuid.uuid4().hex}{ext}"
    path = os.path.join(sub_dir, fname)
    with open(path, "wb") as f:
        f.write(content)

    rel_path = os.path.relpath(path, cfg.media_dir).replace("\\", "/")
    sub = HomeworkSubmission(
        homework_id=homework_id,
        student_id=student.id,
        file_path=rel_path,
        original_filename=file.filename or fname,
        mime_type=mime,
        comment=(comment or "").strip()[:2000],
        status="submitted",
    )
    mark_submission_pending_ai(db, sub)
    db.add(sub)
    db.commit()
    db.refresh(sub)
    if sub.ai_review_status == "pending":
        schedule_ai_review(sub.id)
    return HomeworkSubmissionOut.model_validate(sub)


@router.get("/homework/{homework_id}/submissions/{submission_id}/file")
def portal_download_submission(
    homework_id: int,
    submission_id: int,
    student: Student = Depends(get_current_student),
    db: Session = Depends(get_db),
):
    sub = (
        db.query(HomeworkSubmission)
        .filter(
            HomeworkSubmission.id == submission_id,
            HomeworkSubmission.homework_id == homework_id,
            HomeworkSubmission.student_id == student.id,
        )
        .first()
    )
    if not sub:
        raise HTTPException(status_code=404, detail="Not found")
    cfg = get_settings()
    full = os.path.join(cfg.media_dir, sub.file_path)
    if not os.path.isfile(full):
        raise HTTPException(status_code=404, detail="File missing")
    return FileResponse(full, media_type=sub.mime_type, filename=sub.original_filename)


@router.get("/calendar.ics")
def portal_calendar_ics(student: Student = Depends(get_current_student), db: Session = Depends(get_db)):
    today = date.today()
    lessons = (
        db.query(Lesson)
        .options(joinedload(Lesson.student))
        .filter(
            Lesson.student_id == student.id,
            Lesson.lesson_date >= today - timedelta(days=30),
            Lesson.status != LessonStatus.cancelled.value,
        )
        .order_by(Lesson.lesson_date.asc())
        .all()
    )
    body = build_ics(lessons, calendar_name=f"RepetCRM — {student.name}", student_name=student.name)
    return Response(
        content=body.encode("utf-8"),
        media_type="text/calendar; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="schedule-{student.id}.ics"'},
    )


@router.post("/payments/intent", response_model=PaymentIntentOut, status_code=201)
def portal_create_payment(
    data: PortalPaymentIntentIn,
    student: Student = Depends(get_current_student),
    db: Session = Depends(get_db),
):
    intent = create_payment_intent(
        db,
        tutor_id=student.tutor_id,
        student_id=student.id,
        amount=data.amount,
        provider=data.provider,
        purpose="balance_topup",
    )
    return PaymentIntentOut.model_validate(intent)
