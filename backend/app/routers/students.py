from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models import User, Student, Lesson, Homework, LessonPackage
from app.schemas import (
    StudentCreate,
    StudentUpdate,
    StudentOut,
    StudentListPage,
    StudentLessonsPage,
    StudentLessonHistoryItem,
    StudentHomeworkPage,
    StudentHomeworkItem,
    StudentBoundariesOut,
    BoundaryApplyIn,
    BoundaryMessageOut,
    PortalLinkOut,
    ParentPortalLinkOut,
    ParentMonthlyReportOut,
    MessageOut,
    TrialFollowupOut,
    LessonPackageCreate,
    LessonPackageOut,
    StudentBalanceTopUp,
)
from app.services.boundaries import (
    decide_boundary_mode,
    apply_boundary_mode,
    render_boundary_message,
    BOUNDARY_RULES,
    MODE_SEVERITY,
)
from app.services.dashboard_cache import invalidate_dashboard
from app.services.student_search import apply_student_name_search
from app.services.portal_token import (
    ensure_portal_token,
    regenerate_portal_token,
    ensure_parent_portal_token,
    regenerate_parent_portal_token,
)
from app.services.parent_contact import sync_parent_contact
from app.services.parent_report_service import build_parent_monthly_report, resolve_month
from app.services.parent_report_pdf import generate_parent_report_pdf, read_parent_report_pdf_bytes
from app.services.parent_notifications import send_parent_monthly_report_email
from app.services.trial_funnel_service import get_trial_followup
from app.config import get_settings
from app.models import StudentBoundaryMode

router = APIRouter(prefix="/students", tags=["students"])


def _parse_mode(raw: str | None) -> StudentBoundaryMode:
    value = (raw or StudentBoundaryMode.normal.value).strip().lower()
    try:
        return StudentBoundaryMode(value)
    except ValueError:
        return StudentBoundaryMode.normal


@router.get("", response_model=StudentListPage)
def list_students(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    q: str | None = Query(None, max_length=100, description="Поиск по имени"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    query = db.query(Student)
    query = apply_student_name_search(query, user.id, q)
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
    sync_parent_contact(student)
    db.add(student)
    db.flush()
    ensure_portal_token(db, student)
    ensure_parent_portal_token(db, student)
    db.commit()
    db.refresh(student)
    invalidate_dashboard(user.id)
    return student


@router.get("/{student_id}", response_model=StudentOut)
def get_student(student_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    student = (
        db.query(Student)
        .filter(Student.id == student_id, Student.tutor_id == user.id)
        .first()
    )
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    return student


@router.get("/{student_id}/lessons", response_model=StudentLessonsPage)
def list_student_lessons(
    student_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    student = db.query(Student).filter(Student.id == student_id, Student.tutor_id == user.id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    base = db.query(Lesson).filter(Lesson.tutor_id == user.id, Lesson.student_id == student_id)
    total = base.count()
    offset = (page - 1) * page_size
    rows = (
        base.order_by(Lesson.lesson_date.desc(), Lesson.id.desc())
        .offset(offset)
        .limit(page_size)
        .all()
    )
    lesson_ids = [r.id for r in rows]
    homework_by_lesson: dict[int, int] = {}
    if lesson_ids:
        for hw_id, lesson_id in (
            db.query(Homework.id, Homework.lesson_id)
            .filter(Homework.lesson_id.in_(lesson_ids))
            .all()
        ):
            homework_by_lesson[lesson_id] = hw_id

    items = [
        StudentLessonHistoryItem(
            id=lesson.id,
            lesson_date=lesson.lesson_date,
            homework_id=homework_by_lesson.get(lesson.id),
        )
        for lesson in rows
    ]
    return StudentLessonsPage(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        has_more=offset + len(rows) < total,
    )


@router.get("/{student_id}/homework", response_model=StudentHomeworkPage)
def list_student_homework(
    student_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    student = db.query(Student).filter(Student.id == student_id, Student.tutor_id == user.id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    base = (
        db.query(Homework, Lesson.lesson_date)
        .join(Lesson, Homework.lesson_id == Lesson.id)
        .filter(Lesson.tutor_id == user.id, Lesson.student_id == student_id)
    )
    total = base.count()
    offset = (page - 1) * page_size
    rows = (
        base.order_by(Lesson.lesson_date.desc(), Homework.id.desc())
        .offset(offset)
        .limit(page_size)
        .all()
    )

    def _preview(text: str) -> str:
        clean = " ".join((text or "").split())
        return clean[:200] + ("…" if len(clean) > 200 else "")

    items = [
        StudentHomeworkItem(
            id=hw.id,
            lesson_id=hw.lesson_id,
            lesson_date=lesson_date,
            preview=_preview(hw.homework_text),
            created_at=hw.created_at,
            updated_at=hw.updated_at,
        )
        for hw, lesson_date in rows
    ]
    return StudentHomeworkPage(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        has_more=offset + len(rows) < total,
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
    sync_parent_contact(student)
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


@router.get("/{student_id}/portal-link", response_model=PortalLinkOut)
def get_portal_link(student_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    student = db.query(Student).filter(Student.id == student_id, Student.tutor_id == user.id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    token = ensure_portal_token(db, student)
    db.commit()
    base = get_settings().public_site_url
    return PortalLinkOut(portal_token=token, portal_url=f"{base}/portal?token={token}")


@router.post("/{student_id}/portal-link/regenerate", response_model=PortalLinkOut)
def regenerate_portal_link(
    student_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    student = db.query(Student).filter(Student.id == student_id, Student.tutor_id == user.id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    token = regenerate_portal_token(db, student)
    db.commit()
    base = get_settings().public_site_url
    return PortalLinkOut(portal_token=token, portal_url=f"{base}/portal?token={token}")


@router.get("/{student_id}/parent-portal-link", response_model=ParentPortalLinkOut)
def get_parent_portal_link(student_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    student = db.query(Student).filter(Student.id == student_id, Student.tutor_id == user.id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    token = ensure_parent_portal_token(db, student)
    db.commit()
    base = get_settings().public_site_url
    return ParentPortalLinkOut(
        parent_portal_token=token,
        parent_portal_url=f"{base}/parent?token={token}",
    )


@router.post("/{student_id}/parent-portal-link/regenerate", response_model=ParentPortalLinkOut)
def regenerate_parent_portal_link(
    student_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    student = db.query(Student).filter(Student.id == student_id, Student.tutor_id == user.id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    token = regenerate_parent_portal_token(db, student)
    db.commit()
    base = get_settings().public_site_url
    return ParentPortalLinkOut(
        parent_portal_token=token,
        parent_portal_url=f"{base}/parent?token={token}",
    )


@router.get("/{student_id}/packages", response_model=list[LessonPackageOut])
def list_packages(student_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    student = db.query(Student).filter(Student.id == student_id, Student.tutor_id == user.id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    rows = (
        db.query(LessonPackage)
        .filter(LessonPackage.student_id == student_id, LessonPackage.tutor_id == user.id)
        .order_by(LessonPackage.created_at.desc())
        .all()
    )
    return rows


@router.post("/{student_id}/packages", response_model=LessonPackageOut, status_code=201)
def create_package(
    student_id: int,
    data: LessonPackageCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    student = db.query(Student).filter(Student.id == student_id, Student.tutor_id == user.id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    if data.prepaid_amount > 0:
        student.balance = round(float(student.balance or 0) + data.prepaid_amount, 2)
    pkg = LessonPackage(
        tutor_id=user.id,
        student_id=student_id,
        name=data.name,
        lessons_total=data.lessons_total,
        lessons_remaining=data.lessons_total,
        price_per_lesson=data.price_per_lesson,
        is_active=True,
    )
    db.add(pkg)
    db.commit()
    db.refresh(pkg)
    return pkg


@router.post("/{student_id}/balance", response_model=StudentOut)
def top_up_balance(
    student_id: int,
    data: StudentBalanceTopUp,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    student = db.query(Student).filter(Student.id == student_id, Student.tutor_id == user.id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    student.balance = round(float(student.balance or 0) + data.amount, 2)
    db.commit()
    db.refresh(student)
    return student


@router.get("/{student_id}/trial-followup", response_model=TrialFollowupOut)
def get_student_trial_followup(
    student_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    student = db.query(Student).filter(Student.id == student_id, Student.tutor_id == user.id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    return get_trial_followup(db, student, user.name or "")


@router.get("/{student_id}/parent-report", response_model=ParentMonthlyReportOut)
def get_student_parent_report(
    student_id: int,
    month: str | None = Query(None, description="YYYY-MM"),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    student = db.query(Student).filter(Student.id == student_id, Student.tutor_id == user.id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    try:
        month_key = resolve_month(month)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return build_parent_monthly_report(db, student=student, tutor=user, month=month_key)


@router.get("/{student_id}/parent-report.pdf")
def download_student_parent_report_pdf(
    student_id: int,
    month: str | None = Query(None, description="YYYY-MM"),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    student = db.query(Student).filter(Student.id == student_id, Student.tutor_id == user.id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    try:
        month_key = resolve_month(month)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    report = build_parent_monthly_report(db, student=student, tutor=user, month=month_key)
    path = generate_parent_report_pdf(report, student_id=student.id)
    filename = f"otchet-{student.name.replace(' ', '_')}-{month_key}.pdf"
    return FileResponse(path, media_type="application/pdf", filename=filename)


@router.post("/{student_id}/parent-report/send", response_model=MessageOut)
def send_student_parent_report(
    student_id: int,
    month: str | None = Query(None, description="YYYY-MM"),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    student = db.query(Student).filter(Student.id == student_id, Student.tutor_id == user.id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    if not (student.parent_email or "").strip():
        raise HTTPException(status_code=400, detail="Parent email not set")
    try:
        month_key = resolve_month(month)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    report = build_parent_monthly_report(db, student=student, tutor=user, month=month_key)
    path = generate_parent_report_pdf(report, student_id=student.id)
    pdf_bytes = read_parent_report_pdf_bytes(path)
    if not send_parent_monthly_report_email(
        db, student=student, tutor=user, report=report, pdf_bytes=pdf_bytes
    ):
        raise HTTPException(status_code=502, detail="Could not send email (check SMTP and parent email)")
    db.commit()
    return MessageOut(message="Report sent")
