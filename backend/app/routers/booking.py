"""Public trial lesson booking."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.dependencies import get_current_user
from app.models import TrialBooking, User
from app.schemas import (
    BookingSettingsOut,
    BookingSettingsUpdate,
    BookingTutorPublicOut,
    TrialBookingLeadOut,
    TrialBookingSubmitIn,
    TrialBookingSubmitOut,
)
from app.services.auth_rate_limit import get_register_limiter
from app.services.booking_notifications import send_trial_booking_emails
from app.services.booking_service import (
    booking_public_url,
    compute_available_slots,
    create_trial_booking,
    dump_booking_hours,
    ensure_unique_slug,
    parse_booking_hours,
    suggest_slug,
    tutor_by_booking_slug,
)
from app.services.dashboard_cache import invalidate_dashboard
from app.utils import from_json_list

router = APIRouter(prefix="/book", tags=["booking"])

_BOOKING_LIMIT = 10
_BOOKING_WINDOW_SEC = 3600


def _client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for", "")
    if forwarded:
        return forwarded.split(",")[0].strip() or "unknown"
    if request.client:
        return request.client.host
    return "unknown"


def _settings_out(user: User) -> BookingSettingsOut:
    slug = user.booking_slug or suggest_slug(user)
    return BookingSettingsOut(
        booking_slug=slug,
        booking_enabled=bool(user.booking_enabled),
        booking_hours=parse_booking_hours(user.booking_hours),
        booking_reply_text=user.booking_reply_text or "",
        booking_url=booking_public_url(slug) if user.booking_slug else "",
    )


def _lead_out(booking: TrialBooking) -> TrialBookingLeadOut:
    s = booking.student
    return TrialBookingLeadOut(
        id=booking.id,
        student_id=booking.student_id,
        child_name=s.name,
        grade=s.grade or "",
        subject=s.subject or "",
        parent_name=s.parent_name or "",
        parent_email=s.parent_email or "",
        parent_phone=s.parent_phone or "",
        preferred_date=booking.preferred_date,
        preferred_time=booking.preferred_time,
        parent_message=booking.parent_message or "",
        status=booking.status,
        created_at=booking.created_at,
    )


@router.get("/settings/me", response_model=BookingSettingsOut)
def get_booking_settings(user: User = Depends(get_current_user)):
    return _settings_out(user)


@router.put("/settings/me", response_model=BookingSettingsOut)
def update_booking_settings(
    data: BookingSettingsUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if data.booking_slug is not None:
        user.booking_slug = ensure_unique_slug(db, user, data.booking_slug)
    elif data.booking_enabled and not user.booking_slug:
        user.booking_slug = ensure_unique_slug(db, user, suggest_slug(user))

    if data.booking_enabled is not None:
        if data.booking_enabled and not user.booking_slug:
            user.booking_slug = ensure_unique_slug(db, user, suggest_slug(user))
        user.booking_enabled = data.booking_enabled

    if data.booking_hours is not None:
        user.booking_hours = dump_booking_hours(data.booking_hours)

    if data.booking_reply_text is not None:
        user.booking_reply_text = data.booking_reply_text.strip()

    db.commit()
    db.refresh(user)
    return _settings_out(user)


@router.get("/leads/me", response_model=list[TrialBookingLeadOut])
def list_trial_leads(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    rows = (
        db.query(TrialBooking)
        .options(joinedload(TrialBooking.student))
        .filter(TrialBooking.tutor_id == user.id)
        .order_by(TrialBooking.created_at.desc())
        .limit(50)
        .all()
    )
    return [_lead_out(b) for b in rows]


@router.patch("/leads/{booking_id}", response_model=TrialBookingLeadOut)
def update_trial_lead_status(
    booking_id: int,
    status: str = Query(...),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    allowed = {"new", "contacted", "scheduled", "declined"}
    value = (status or "").strip().lower()
    if value not in allowed:
        raise HTTPException(status_code=400, detail=f"status must be one of: {', '.join(sorted(allowed))}")

    booking = (
        db.query(TrialBooking)
        .options(joinedload(TrialBooking.student))
        .filter(TrialBooking.id == booking_id, TrialBooking.tutor_id == user.id)
        .first()
    )
    if not booking:
        raise HTTPException(status_code=404, detail="Lead not found")
    booking.status = value
    db.commit()
    db.refresh(booking)
    return _lead_out(booking)


@router.get("/{slug}", response_model=BookingTutorPublicOut)
def public_booking_page(slug: str, db: Session = Depends(get_db)):
    tutor = tutor_by_booking_slug(db, slug)
    if not tutor:
        raise HTTPException(status_code=404, detail="Booking page not found")
    return BookingTutorPublicOut(
        tutor_name=tutor.name or "",
        subjects=from_json_list(tutor.subjects),
        grade_levels=from_json_list(tutor.grade_levels),
        teaching_format=tutor.teaching_format or "",
        slots=compute_available_slots(db, tutor),
    )


@router.post("/{slug}", response_model=TrialBookingSubmitOut, status_code=201)
def submit_trial_booking(
    slug: str,
    data: TrialBookingSubmitIn,
    request: Request,
    db: Session = Depends(get_db),
):
    ip = _client_ip(request)
    limiter = get_register_limiter(_BOOKING_LIMIT, _BOOKING_WINDOW_SEC)
    rate_key = f"book:{slug}:{ip}"
    if limiter.is_blocked(rate_key):
        raise HTTPException(status_code=429, detail="Too many requests. Try again later.")
    limiter.record(rate_key)

    tutor = tutor_by_booking_slug(db, slug)
    if not tutor:
        raise HTTPException(status_code=404, detail="Booking page not found")

    booking = create_trial_booking(db, tutor, data)
    send_trial_booking_emails(db, tutor=tutor, booking=booking)
    db.commit()
    invalidate_dashboard(tutor.id)
    return TrialBookingSubmitOut(
        message="Заявка принята. Мы свяжемся с вами для подтверждения времени.",
        booking_id=booking.id,
    )
