"""SMTP email delivery."""

from __future__ import annotations

import logging
import smtplib
from email.message import EmailMessage

from app.config import get_settings

logger = logging.getLogger(__name__)


def smtp_configured() -> bool:
    cfg = get_settings()
    return bool(cfg.smtp_host.strip() and cfg.smtp_from.strip())


def send_email(*, to: str, subject: str, body: str) -> bool:
    return send_email_with_attachment(to=to, subject=subject, body=body)


def send_email_with_attachment(
    *,
    to: str,
    subject: str,
    body: str,
    attachment_filename: str | None = None,
    attachment_bytes: bytes | None = None,
    attachment_mime: str = "application/pdf",
) -> bool:
    cfg = get_settings()
    if not smtp_configured():
        logger.warning("SMTP not configured — email not sent to %s: %s", to, subject)
        return False

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = cfg.smtp_from
    msg["To"] = to
    msg.set_content(body)
    if attachment_filename and attachment_bytes:
        msg.add_attachment(
            attachment_bytes,
            maintype=attachment_mime.split("/")[0],
            subtype=attachment_mime.split("/")[-1],
            filename=attachment_filename,
        )

    try:
        with smtplib.SMTP(cfg.smtp_host, cfg.smtp_port, timeout=20) as smtp:
            if cfg.smtp_use_tls:
                smtp.starttls()
            user = cfg.smtp_user.strip()
            password = cfg.smtp_password
            if user and password:
                smtp.login(user, password)
            smtp.send_message(msg)
        logger.info("email sent to=%s subject=%s", to, subject)
        return True
    except Exception as exc:
        logger.error("email failed to=%s: %s", to, exc)
        return False
