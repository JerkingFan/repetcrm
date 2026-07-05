"""Email notifications for trial booking."""

from __future__ import annotations

import logging

from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import TrialBooking, User
from app.services.booking_service import booking_public_url
from app.services.mailer import send_email

logger = logging.getLogger(__name__)

_DEFAULT_REPLY = (
    "Спасибо за заявку на пробное занятие!\n\n"
    "Я получил(а) вашу заявку и свяжусь с вами в ближайшее время для подтверждения времени.\n\n"
    "С уважением,\n{tutor_name}"
)


def send_trial_booking_emails(db: Session, *, tutor: User, booking: TrialBooking) -> None:
    student = booking.student
    slot_label = f"{booking.preferred_date.strftime('%d.%m.%Y')} {booking.preferred_time}"
    cfg = get_settings()
    crm_hint = cfg.public_site_url

    tutor_subject = f"Новая заявка на пробный: {student.name}"
    tutor_body = (
        f"Новая заявка с публичной страницы.\n\n"
        f"Ученик: {student.name}\n"
        f"Класс: {student.grade}\n"
        f"Предмет: {student.subject}\n"
        f"Родитель: {student.parent_name}\n"
        f"Email: {student.parent_email}\n"
        f"Телефон: {student.parent_phone or '—'}\n"
        f"Желаемое время: {slot_label}\n"
    )
    if booking.parent_message:
        tutor_body += f"\nСообщение: {booking.parent_message}\n"
    tutor_body += f"\nКарточка ученика: {crm_hint}/students/{student.id}\n"

    if tutor.notify_email:
        if not send_email(to=tutor.email, subject=tutor_subject, body=tutor_body):
            logger.warning("trial booking tutor email failed tutor_id=%s", tutor.id)
    else:
        logger.info("trial booking tutor email skipped (notify_email off) tutor_id=%s", tutor.id)

    parent_to = (student.parent_email or "").strip()
    if parent_to:
        reply_template = (tutor.booking_reply_text or "").strip() or _DEFAULT_REPLY
        parent_body = reply_template.format(tutor_name=tutor.name or "Репетитор")
        parent_subject = f"Заявка принята — {tutor.name or 'репетитор'}"
        if not send_email(to=parent_to, subject=parent_subject, body=parent_body):
            logger.warning("trial booking parent email failed booking_id=%s", booking.id)
