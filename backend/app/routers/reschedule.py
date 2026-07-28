"""Tutor endpoints for student reschedule requests."""

from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.dependencies import get_current_user
from app.models import Lesson, LessonRescheduleRequest, User
from app.schemas import RescheduleResolveIn, RescheduleRequestOut

router = APIRouter(prefix="/reschedule-requests", tags=["reschedule"])


@router.get("", response_model=list[RescheduleRequestOut])
def list_reschedule_requests(
    status: str = "pending",
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    q = (
        db.query(LessonRescheduleRequest)
        .options(
            joinedload(LessonRescheduleRequest.student),
            joinedload(LessonRescheduleRequest.lesson),
        )
        .filter(LessonRescheduleRequest.tutor_id == user.id)
        .order_by(LessonRescheduleRequest.created_at.desc())
    )
    if status and status != "all":
        q = q.filter(LessonRescheduleRequest.status == status)
    rows = q.limit(50).all()
    return [
        RescheduleRequestOut(
            id=r.id,
            lesson_id=r.lesson_id,
            student_id=r.student_id,
            student_name=r.student.name if r.student else "",
            lesson_date=r.lesson.lesson_date if r.lesson else datetime.utcnow().date(),
            lesson_time=(r.lesson.lesson_time if r.lesson else "") or "10:00",
            message=r.message or "",
            preferred_date=r.preferred_date,
            preferred_time=r.preferred_time or "",
            status=r.status,
            tutor_note=r.tutor_note or "",
            created_at=r.created_at,
        )
        for r in rows
    ]


@router.post("/{request_id}/resolve", response_model=RescheduleRequestOut)
def resolve_reschedule_request(
    request_id: int,
    data: RescheduleResolveIn,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    req = (
        db.query(LessonRescheduleRequest)
        .options(
            joinedload(LessonRescheduleRequest.student),
            joinedload(LessonRescheduleRequest.lesson),
        )
        .filter(LessonRescheduleRequest.id == request_id, LessonRescheduleRequest.tutor_id == user.id)
        .first()
    )
    if not req:
        raise HTTPException(status_code=404, detail="Not found")
    if req.status != "pending":
        raise HTTPException(status_code=400, detail="Already resolved")
    req.status = data.status
    req.tutor_note = (data.tutor_note or "").strip()[:1000]
    req.resolved_at = datetime.utcnow()
    if data.status == "approved" and req.lesson and not req.lesson.is_conducted:
        if req.preferred_date:
            req.lesson.lesson_date = req.preferred_date
        if req.preferred_time:
            req.lesson.lesson_time = req.preferred_time.strip()[:5]
    db.commit()
    db.refresh(req)
    return RescheduleRequestOut(
        id=req.id,
        lesson_id=req.lesson_id,
        student_id=req.student_id,
        student_name=req.student.name if req.student else "",
        lesson_date=req.lesson.lesson_date if req.lesson else datetime.utcnow().date(),
        lesson_time=(req.lesson.lesson_time if req.lesson else "") or "10:00",
        message=req.message or "",
        preferred_date=req.preferred_date,
        preferred_time=req.preferred_time or "",
        status=req.status,
        tutor_note=req.tutor_note or "",
        created_at=req.created_at,
    )
