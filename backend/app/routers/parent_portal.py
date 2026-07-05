"""Parent cabinet: schedule, balance, payments (no homework)."""

from __future__ import annotations

from datetime import date, timedelta

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, Request, Response, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.auth import create_parent_portal_session_token
from app.database import get_db
from app.models import Homework, HomeworkSubmission, Lesson, LessonPackage, LessonStatus, Student, User, PaymentReceipt
from app.parent_portal_cookies import clear_parent_portal_cookie, set_parent_portal_cookie
from app.parent_portal_dependencies import get_current_parent_student
from app.schemas import (
    ParentPortalLoginIn,
    ParentPortalOut,
    ParentPortalPackageOut,
    ParentHomeworkStatusOut,
    ParentMonthlyReportOut,
    PaymentIntentOut,
    PortalLessonOut,
    PortalPaymentIntentIn,
    ParentPaymentDetailsOut,
    PaymentReceiptOut,
)
from app.services.parent_report_service import build_parent_monthly_report, resolve_month
from app.services.parent_report_pdf import generate_parent_report_pdf, read_parent_report_pdf_bytes
from app.services.homework_submission_review import latest_submission_status, status_label
from app.services.auth_rate_limit import get_register_limiter
from app.services.payment_service import create_payment_intent
from app.services.manual_payment_service import create_payment_receipt, save_receipt_file
from app.services.dashboard_cache import invalidate_dashboard
from app.config import get_settings
from app.services.portal_token import student_by_parent_portal_token
from app.services.ics_calendar import build_ics

router = APIRouter(prefix="/parent-portal", tags=["parent-portal"])

_PARENT_LOGIN_LIMIT = 20
_PARENT_LOGIN_WINDOW_SEC = 300


def _client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for", "")
    if forwarded:
        return forwarded.split(",")[0].strip() or "unknown"
    if request.client:
        return request.client.host
    return "unknown"


def _parent_out(student: Student, tutor: User | None) -> ParentPortalOut:
    return ParentPortalOut(
        student_id=student.id,
        student_name=student.name,
        subject=student.subject or "",
        grade=student.grade or "",
        parent_name=student.parent_name or "",
        balance=float(student.balance or 0),
        tutor_name=tutor.name if tutor else "",
    )


@router.post("/session", response_model=ParentPortalOut)
def parent_portal_login(
    data: ParentPortalLoginIn,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
):
    ip = _client_ip(request)
    limiter = get_register_limiter(_PARENT_LOGIN_LIMIT, _PARENT_LOGIN_WINDOW_SEC)
    rate_key = f"parent_portal:{ip}"
    if limiter.is_blocked(rate_key):
        raise HTTPException(
            status_code=429,
            detail="Too many login attempts. Try again later.",
            headers={"Retry-After": str(limiter.retry_after_sec(rate_key))},
        )
    limiter.record(rate_key)

    student = student_by_parent_portal_token(db, data.parent_portal_token)
    if not student:
        raise HTTPException(status_code=400, detail="Invalid parent link")
    tutor = db.query(User).filter(User.id == student.tutor_id).first()
    session = create_parent_portal_session_token(student.id)
    set_parent_portal_cookie(response, session)
    return _parent_out(student, tutor)


@router.post("/logout")
def parent_portal_logout(response: Response):
    clear_parent_portal_cookie(response)
    return {"ok": True}


@router.get("/me", response_model=ParentPortalOut)
def parent_portal_me(
    student: Student = Depends(get_current_parent_student),
    db: Session = Depends(get_db),
):
    tutor = db.query(User).filter(User.id == student.tutor_id).first()
    return _parent_out(student, tutor)


@router.get("/lessons", response_model=list[PortalLessonOut])
def parent_portal_lessons(
    student: Student = Depends(get_current_parent_student),
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


@router.get("/packages", response_model=list[ParentPortalPackageOut])
def parent_portal_packages(
    student: Student = Depends(get_current_parent_student),
    db: Session = Depends(get_db),
):
    rows = (
        db.query(LessonPackage)
        .filter(LessonPackage.student_id == student.id, LessonPackage.is_active.is_(True))
        .order_by(LessonPackage.created_at.desc())
        .all()
    )
    return [ParentPortalPackageOut.model_validate(p) for p in rows]


@router.get("/homework-status", response_model=list[ParentHomeworkStatusOut])
def parent_portal_homework_status(
    student: Student = Depends(get_current_parent_student),
    db: Session = Depends(get_db),
):
    rows = (
        db.query(Homework, Lesson)
        .join(Lesson, Homework.lesson_id == Lesson.id)
        .filter(Lesson.student_id == student.id)
        .order_by(Lesson.lesson_date.desc())
        .limit(30)
        .all()
    )
    hw_ids = [hw.id for hw, _ in rows]
    subs_by_hw: dict[int, list] = {}
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

    out: list[ParentHomeworkStatusOut] = []
    for hw, lesson in rows:
        subs = subs_by_hw.get(hw.id, [])
        status = latest_submission_status(subs)
        latest = max(subs, key=lambda s: s.submitted_at) if subs else None
        out.append(
            ParentHomeworkStatusOut(
                homework_id=hw.id,
                lesson_id=lesson.id,
                lesson_date=lesson.lesson_date,
                status=status,
                status_label=status_label(status),
                reviewed_at=latest.reviewed_at if latest else None,
            )
        )
    return out


@router.get("/report", response_model=ParentMonthlyReportOut)
def parent_portal_report(
    student: Student = Depends(get_current_parent_student),
    db: Session = Depends(get_db),
    month: str | None = Query(None, description="YYYY-MM"),
):
    tutor = db.query(User).filter(User.id == student.tutor_id).first()
    if not tutor:
        raise HTTPException(status_code=404, detail="Tutor not found")
    try:
        month_key = resolve_month(month)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return build_parent_monthly_report(db, student=student, tutor=tutor, month=month_key)


@router.get("/report.pdf")
def parent_portal_report_pdf(
    student: Student = Depends(get_current_parent_student),
    db: Session = Depends(get_db),
    month: str | None = Query(None, description="YYYY-MM"),
):
    tutor = db.query(User).filter(User.id == student.tutor_id).first()
    if not tutor:
        raise HTTPException(status_code=404, detail="Tutor not found")
    try:
        month_key = resolve_month(month)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    report = build_parent_monthly_report(db, student=student, tutor=tutor, month=month_key)
    path = generate_parent_report_pdf(report, student_id=student.id)
    filename = f"otchet-{student.name.replace(' ', '_')}-{month_key}.pdf"
    return Response(
        content=read_parent_report_pdf_bytes(path),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post("/payments/intent", response_model=PaymentIntentOut, status_code=201)
def parent_portal_create_payment(
    data: PortalPaymentIntentIn,
    student: Student = Depends(get_current_parent_student),
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


@router.get("/payment-details", response_model=ParentPaymentDetailsOut)
def parent_portal_payment_details(
    student: Student = Depends(get_current_parent_student),
    db: Session = Depends(get_db),
):
    tutor = db.query(User).filter(User.id == student.tutor_id).first()
    details = (tutor.payment_details or "").strip() if tutor else ""
    return ParentPaymentDetailsOut(
        tutor_name=tutor.name if tutor else "",
        payment_details=details,
        has_requisites=bool(details),
    )


def _parent_receipt_out(receipt: PaymentReceipt, student: Student) -> PaymentReceiptOut:
    return PaymentReceiptOut(
        id=receipt.id,
        student_id=receipt.student_id,
        student_name=student.name,
        amount=float(receipt.amount),
        status=receipt.status,
        original_filename=receipt.original_filename,
        parent_note=receipt.parent_note or "",
        tutor_note=receipt.tutor_note or "",
        created_at=receipt.created_at,
        reviewed_at=receipt.reviewed_at,
    )


@router.get("/payments/receipts", response_model=list[PaymentReceiptOut])
def parent_portal_list_receipts(
    student: Student = Depends(get_current_parent_student),
    db: Session = Depends(get_db),
):
    rows = (
        db.query(PaymentReceipt)
        .filter(PaymentReceipt.student_id == student.id)
        .order_by(PaymentReceipt.created_at.desc())
        .limit(20)
        .all()
    )
    return [_parent_receipt_out(r, student) for r in rows]


@router.post("/payments/receipt", response_model=PaymentReceiptOut, status_code=201)
async def parent_portal_submit_receipt(
    student: Student = Depends(get_current_parent_student),
    db: Session = Depends(get_db),
    amount: float = Form(...),
    note: str = Form(""),
    file: UploadFile = File(...),
):
    tutor = db.query(User).filter(User.id == student.tutor_id).first()
    if not tutor or not (tutor.payment_details or "").strip():
        raise HTTPException(
            status_code=400,
            detail="Репетитор ещё не указал реквизиты для оплаты",
        )
    receipt = create_payment_receipt(
        db,
        tutor_id=student.tutor_id,
        student_id=student.id,
        amount=amount,
        parent_note=note,
    )
    cfg = get_settings()
    rel_path, mime, orig = await save_receipt_file(cfg, receipt_id=receipt.id, file=file)
    receipt.file_path = rel_path
    receipt.mime_type = mime
    receipt.original_filename = orig
    db.commit()
    invalidate_dashboard(student.tutor_id)
    db.refresh(receipt)
    return _parent_receipt_out(receipt, student)


@router.get("/payments/receipts/{receipt_id}/file")
def parent_portal_receipt_file(
    receipt_id: int,
    student: Student = Depends(get_current_parent_student),
    db: Session = Depends(get_db),
):
    import os

    receipt = (
        db.query(PaymentReceipt)
        .filter(PaymentReceipt.id == receipt_id, PaymentReceipt.student_id == student.id)
        .first()
    )
    if not receipt or not receipt.file_path:
        raise HTTPException(status_code=404, detail="Not found")
    cfg = get_settings()
    path = os.path.join(cfg.media_dir, receipt.file_path.replace("/", os.sep))
    if not os.path.isfile(path):
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(path, media_type=receipt.mime_type, filename=receipt.original_filename)


@router.get("/calendar.ics")
def parent_portal_calendar_ics(
    student: Student = Depends(get_current_parent_student),
    db: Session = Depends(get_db),
):
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
    body = build_ics(
        lessons,
        calendar_name=f"Занятия — {student.name}",
        student_name=student.name,
    )
    return Response(
        content=body.encode("utf-8"),
        media_type="text/calendar; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="parent-schedule-{student.id}.ics"'},
    )
