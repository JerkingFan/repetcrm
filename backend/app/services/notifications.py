"""Email and Telegram notifications with deduplication."""

from __future__ import annotations

import logging

import httpx
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import NotificationLog, User
from app.services.mailer import send_email

logger = logging.getLogger(__name__)


def _already_sent(db: Session, ref_key: str) -> bool:
    return db.query(NotificationLog.id).filter(NotificationLog.ref_key == ref_key).first() is not None


def _mark_sent(db: Session, user_id: int, kind: str, ref_key: str) -> None:
    db.add(NotificationLog(user_id=user_id, kind=kind, ref_key=ref_key))
    db.flush()


def send_telegram(chat_id: str, text: str) -> bool:
    cfg = get_settings()
    token = cfg.telegram_bot_token.strip()
    if not token or not chat_id.strip():
        return False
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    try:
        with httpx.Client(timeout=15.0) as client:
            r = client.post(url, json={"chat_id": chat_id.strip(), "text": text})
            if r.status_code == 200:
                return True
            logger.warning("telegram send failed: %s %s", r.status_code, r.text[:200])
    except Exception as exc:
        logger.warning("telegram error: %s", exc)
    return False


def notify_user(db: Session, user: User, *, kind: str, ref_key: str, subject: str, body: str) -> bool:
    if _already_sent(db, ref_key):
        return False

    delivered = False
    if user.notify_email:
        if send_email(to=user.email, subject=subject, body=body):
            delivered = True
    if user.notify_telegram and user.telegram_chat_id.strip():
        if send_telegram(user.telegram_chat_id, f"{subject}\n\n{body}"):
            delivered = True

    if delivered:
        _mark_sent(db, user.id, kind, ref_key)
    return delivered


def notify_homework_ready(db: Session, user: User, *, lesson_id: int, student_name: str) -> None:
    if not user.notify_homework_ready:
        return
    ref_key = f"homework_ready:{user.id}:{lesson_id}"
    subject = "RepetCRM: ДЗ готово"
    body = f"Домашнее задание для {student_name} сгенерировано. Откройте урок #{lesson_id} в CRM."
    notify_user(db, user, kind="homework_ready", ref_key=ref_key, subject=subject, body=body)
