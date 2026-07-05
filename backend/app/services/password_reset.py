"""Password reset token lifecycle."""

from __future__ import annotations

import hashlib
import logging
import secrets
from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import PasswordResetToken, User
from app.services.mailer import send_email

logger = logging.getLogger(__name__)


def _hash_token(raw: str) -> str:
    return hashlib.sha256(raw.encode()).hexdigest()


def create_reset_token(db: Session, user: User) -> str:
    cfg = get_settings()
    raw = secrets.token_urlsafe(32)
    token_hash = _hash_token(raw)
    expires = datetime.utcnow() + timedelta(hours=cfg.password_reset_expire_hours)

    db.query(PasswordResetToken).filter(
        PasswordResetToken.user_id == user.id,
        PasswordResetToken.used_at.is_(None),
    ).update({PasswordResetToken.used_at: datetime.utcnow()})

    db.add(
        PasswordResetToken(
            user_id=user.id,
            token_hash=token_hash,
            expires_at=expires,
        )
    )
    db.flush()
    return raw


def send_reset_email(user: User, raw_token: str) -> None:
    cfg = get_settings()
    base = cfg.public_site_url
    link = f"{base}/reset-password?token={raw_token}"
    subject = "RepetCRM — восстановление пароля"
    body = (
        f"Здравствуйте, {user.name or user.email}!\n\n"
        f"Перейдите по ссылке, чтобы задать новый пароль (действует {cfg.password_reset_expire_hours} ч.):\n"
        f"{link}\n\n"
        "Если вы не запрашивали сброс — просто проигнорируйте это письмо."
    )
    sent = send_email(to=user.email, subject=subject, body=body)
    if not sent and not cfg.is_production:
        logger.info("DEV password reset link for %s: %s", user.email, link)


def consume_reset_token(db: Session, raw_token: str) -> User | None:
    token_hash = _hash_token(raw_token)
    row = (
        db.query(PasswordResetToken)
        .filter(
            PasswordResetToken.token_hash == token_hash,
            PasswordResetToken.used_at.is_(None),
            PasswordResetToken.expires_at > datetime.utcnow(),
        )
        .first()
    )
    if not row:
        return None
    user = db.query(User).filter(User.id == row.user_id).first()
    if not user:
        return None
    row.used_at = datetime.utcnow()
    return user
