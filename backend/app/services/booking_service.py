"""Public trial booking: slots, slug, lead creation."""

from __future__ import annotations

import json
import re
from datetime import date, datetime, time, timedelta

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import Lesson, LessonStatus, Student, TrialBooking, User
from app.schemas import BookingHoursSlot, BookingSlotOut, TrialBookingSubmitIn
from app.services.parent_contact import sync_parent_contact
from app.services.portal_token import ensure_parent_portal_token, ensure_portal_token

_SLUG_RE = re.compile(r"^[a-z0-9](?:[a-z0-9-]{1,46}[a-z0-9])?$")

WEEKDAY_LABELS = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]


def default_booking_hours() -> list[dict]:
    return [{"weekday": d, "from": "10:00", "to": "18:00"} for d in range(5)]


def booking_public_url(slug: str) -> str:
    cfg = get_settings()
    base = (cfg.frontend_public_url or "http://localhost:3000").rstrip("/")
    return f"{base}/book/{slug}"


def parse_booking_hours(raw: str) -> list[BookingHoursSlot]:
    try:
        data = json.loads(raw or "[]")
    except json.JSONDecodeError:
        return [BookingHoursSlot.model_validate(x) for x in default_booking_hours()]
    if not isinstance(data, list) or not data:
        return [BookingHoursSlot.model_validate(x) for x in default_booking_hours()]
    return [BookingHoursSlot.model_validate(x) for x in data]


def dump_booking_hours(slots: list[BookingHoursSlot]) -> str:
    return json.dumps([s.model_dump() for s in slots], ensure_ascii=False)


def normalize_slug(raw: str) -> str:
    slug = (raw or "").strip().lower()
    slug = re.sub(r"[^a-z0-9-]+", "-", slug)
    slug = re.sub(r"-{2,}", "-", slug).strip("-")
    return slug


def suggest_slug(user: User) -> str:
    base = normalize_slug(user.name) or user.email.split("@")[0].lower()
    base = base[:40] or f"tutor-{user.id}"
    candidate = base
    n = 1
    while len(candidate) < 3:
        candidate = f"{base}-{n}"
        n += 1
    return candidate


def validate_slug(slug: str) -> str:
    normalized = normalize_slug(slug)
    if not normalized or not _SLUG_RE.match(normalized):
        raise ValueError("slug must be 3-48 chars: lowercase letters, digits, hyphens")
    return normalized


def tutor_by_booking_slug(db: Session, slug: str) -> User | None:
    return (
        db.query(User)
        .filter(User.booking_slug == slug, User.booking_enabled.is_(True))
        .first()
    )


def ensure_unique_slug(db: Session, user: User, slug: str) -> str:
    normalized = validate_slug(slug)
    existing = (
        db.query(User)
        .filter(User.booking_slug == normalized, User.id != user.id)
        .first()
    )
    if existing:
        raise ValueError("This booking link is already taken")
    return normalized


def _parse_hhmm(value: str) -> time:
    parts = (value or "10:00").strip().split(":")
    hour, minute = int(parts[0]), int(parts[1]) if len(parts) > 1 else 0
    return time(hour, minute)


def _time_slots(from_t: str, to_t: str, step_minutes: int = 60) -> list[str]:
    start = _parse_hhmm(from_t)
    end = _parse_hhmm(to_t)
    start_dt = datetime.combine(date.today(), start)
    end_dt = datetime.combine(date.today(), end)
    out: list[str] = []
    cur = start_dt
    while cur < end_dt:
        out.append(cur.strftime("%H:%M"))
        cur += timedelta(minutes=step_minutes)
    return out


def compute_available_slots(
    db: Session,
    tutor: User,
    *,
    days_ahead: int = 14,
    max_slots: int = 40,
) -> list[BookingSlotOut]:
    hours = parse_booking_hours(tutor.booking_hours)
    by_weekday = {h.weekday: h for h in hours}
    if not by_weekday:
        return []

    today = date.today()
    end = today + timedelta(days=days_ahead)
    busy = {
        (row.lesson_date, row.lesson_time or "10:00")
        for row in db.query(Lesson.lesson_date, Lesson.lesson_time)
        .filter(
            Lesson.tutor_id == tutor.id,
            Lesson.lesson_date >= today,
            Lesson.lesson_date <= end,
            Lesson.status != LessonStatus.cancelled.value,
        )
        .all()
    }

    slots: list[BookingSlotOut] = []
    cur = today + timedelta(days=1)
    while cur <= end and len(slots) < max_slots:
        rule = by_weekday.get(cur.weekday())
        if rule:
            for slot_time in _time_slots(rule.from_time, rule.to_time):
                if (cur, slot_time) not in busy:
                    label = f"{WEEKDAY_LABELS[cur.weekday()]} {cur.strftime('%d.%m')} {slot_time}"
                    slots.append(BookingSlotOut(date=cur, time=slot_time, label=label))
                    if len(slots) >= max_slots:
                        break
        cur += timedelta(days=1)
    return slots


def slot_is_available(db: Session, tutor: User, lesson_date: date, lesson_time: str) -> bool:
    if lesson_date <= date.today():
        return False
    hours = parse_booking_hours(tutor.booking_hours)
    rule = next((h for h in hours if h.weekday == lesson_date.weekday()), None)
    if not rule:
        return False
    if lesson_time not in _time_slots(rule.from_time, rule.to_time):
        return False
    clash = (
        db.query(Lesson.id)
        .filter(
            Lesson.tutor_id == tutor.id,
            Lesson.lesson_date == lesson_date,
            Lesson.lesson_time == lesson_time,
            Lesson.status != LessonStatus.cancelled.value,
        )
        .first()
    )
    return clash is None


def create_trial_booking(
    db: Session,
    tutor: User,
    data: TrialBookingSubmitIn,
) -> TrialBooking:
    if not slot_is_available(db, tutor, data.preferred_date, data.preferred_time):
        raise HTTPException(status_code=400, detail="Selected time slot is not available")

    note_parts = [
        f"Заявка с публичной страницы: {data.preferred_date.isoformat()} {data.preferred_time}",
    ]
    if data.message.strip():
        note_parts.append(f"Сообщение: {data.message.strip()}")

    student = Student(
        tutor_id=tutor.id,
        name=data.child_name.strip(),
        subject=data.subject.strip(),
        grade=data.grade.strip(),
        parent_name=data.parent_name.strip(),
        parent_email=data.parent_email.strip(),
        parent_phone=data.parent_phone.strip(),
        parent_notify_email=True,
        notes="\n".join(note_parts),
        student_status="lead",
    )
    sync_parent_contact(student)
    db.add(student)
    db.flush()
    ensure_portal_token(db, student)
    ensure_parent_portal_token(db, student)

    booking = TrialBooking(
        tutor_id=tutor.id,
        student_id=student.id,
        preferred_date=data.preferred_date,
        preferred_time=data.preferred_time,
        parent_message=data.message.strip(),
        status="new",
    )
    db.add(booking)
    db.flush()
    return booking
