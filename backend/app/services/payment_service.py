"""Online payments: ERIP, card, webhook confirmation."""

from __future__ import annotations

import hashlib
import hmac
import json
import secrets
from datetime import datetime, timedelta

from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import Lesson, LessonPackage, PaymentIntent, PaymentTransaction, Student, User


def _public_pay_url(token: str) -> str:
    cfg = get_settings()
    base = cfg.public_site_url
    return f"{base}/pay/{token}"


def _erip_code(intent_id: int) -> str:
    return f"REPET{intent_id:08d}"


def create_payment_intent(
    db: Session,
    *,
    tutor_id: int,
    student_id: int,
    amount: float,
    provider: str,
    purpose: str = "balance_topup",
    purpose_ref_id: int | None = None,
) -> PaymentIntent:
    if amount <= 0:
        raise HTTPException(status_code=400, detail="Сумма должна быть больше 0")
    if provider not in ("erip", "card"):
        raise HTTPException(status_code=400, detail="provider: erip или card")

    student = (
        db.query(Student)
        .filter(Student.id == student_id, Student.tutor_id == tutor_id)
        .first()
    )
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    token = secrets.token_urlsafe(24)
    intent = PaymentIntent(
        tutor_id=tutor_id,
        student_id=student_id,
        amount=round(float(amount), 2),
        provider=provider,
        purpose=purpose,
        purpose_ref_id=purpose_ref_id,
        status="pending",
        public_token=token,
        expires_at=datetime.utcnow() + timedelta(hours=24),
    )
    db.add(intent)
    db.flush()

    intent.erip_code = _erip_code(intent.id) if provider == "erip" else None
    intent.payment_url = _public_pay_url(token)
    intent.external_order_id = f"repet-{intent.id}-{secrets.token_hex(4)}"
    db.commit()
    db.refresh(intent)
    return intent


def mark_lesson_paid(
    db: Session,
    lesson: Lesson,
    *,
    source: str,
    paid_at: datetime | None = None,
) -> None:
    if lesson.is_paid:
        return
    lesson.is_paid = True
    lesson.payment_source = source
    lesson.paid_at = paid_at or datetime.utcnow()


def apply_payment_success(
    db: Session,
    intent: PaymentIntent,
    *,
    external_id: str,
    raw_payload: str = "",
) -> PaymentTransaction:
    # Lock intent row when the dialect supports it (Postgres); no-op-ish on SQLite.
    intent = (
        db.query(PaymentIntent)
        .filter(PaymentIntent.id == intent.id)
        .with_for_update()
        .first()
    ) or intent

    if intent.status == "paid":
        existing = (
            db.query(PaymentTransaction)
            .filter(
                PaymentTransaction.provider == intent.provider,
                PaymentTransaction.external_id == external_id,
            )
            .first()
        )
        if existing:
            return existing
        raise HTTPException(status_code=409, detail="Already paid")

    dup = (
        db.query(PaymentTransaction)
        .filter(
            PaymentTransaction.provider == intent.provider,
            PaymentTransaction.external_id == external_id,
        )
        .first()
    )
    if dup:
        return dup

    now = datetime.utcnow()
    intent.status = "paid"
    intent.paid_at = now

    tx = PaymentTransaction(
        intent_id=intent.id,
        tutor_id=intent.tutor_id,
        student_id=intent.student_id,
        amount=intent.amount,
        currency=intent.currency,
        provider=intent.provider,
        external_id=external_id,
        status="paid",
        raw_payload=raw_payload[:8000],
    )
    db.add(tx)

    student = (
        db.query(Student)
        .filter(Student.id == intent.student_id)
        .with_for_update()
        .first()
    )
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    if intent.purpose == "balance_topup":
        student.balance = round(float(student.balance or 0) + intent.amount, 2)
    elif intent.purpose == "lesson" and intent.purpose_ref_id:
        lesson = (
            db.query(Lesson)
            .filter(
                Lesson.id == intent.purpose_ref_id,
                Lesson.student_id == intent.student_id,
                Lesson.tutor_id == intent.tutor_id,
            )
            .with_for_update()
            .first()
        )
        if lesson:
            mark_lesson_paid(db, lesson, source=intent.provider, paid_at=now)
    elif intent.purpose == "package" and intent.purpose_ref_id:
        package = (
            db.query(LessonPackage)
            .filter(
                LessonPackage.id == intent.purpose_ref_id,
                LessonPackage.student_id == intent.student_id,
            )
            .first()
        )
        if package:
            student.balance = round(float(student.balance or 0) + intent.amount, 2)

    tutor = db.query(User).filter(User.id == intent.tutor_id).first()
    if student and tutor:
        from app.services.parent_notifications import notify_parent_payment_received

        notify_parent_payment_received(db, student=student, tutor=tutor, intent=intent)

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        existing = (
            db.query(PaymentTransaction)
            .filter(
                PaymentTransaction.provider == intent.provider,
                PaymentTransaction.external_id == external_id,
            )
            .first()
        )
        if existing:
            return existing
        raise
    db.refresh(tx)
    return tx


def verify_webhook_signature(body: bytes, signature: str | None) -> bool:
    cfg = get_settings()
    secret = (cfg.payment_webhook_secret or "").strip()
    if not secret:
        return cfg.app_env != "production"
    if not signature:
        return False
    expected = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature.strip())


def process_payment_webhook(db: Session, payload: dict) -> PaymentTransaction:
    intent_id = payload.get("intent_id")
    external_id = payload.get("external_id") or payload.get("transaction_id")
    status = (payload.get("status") or "").lower()

    if not intent_id or not external_id:
        raise HTTPException(status_code=400, detail="intent_id and external_id required")
    if status not in ("paid", "success", "completed"):
        raise HTTPException(status_code=400, detail="Payment not successful")

    intent = db.query(PaymentIntent).filter(PaymentIntent.id == int(intent_id)).first()
    if not intent:
        raise HTTPException(status_code=404, detail="Intent not found")
    if intent.status == "expired" or (
        intent.expires_at < datetime.utcnow() and intent.status != "paid"
    ):
        raise HTTPException(status_code=410, detail="Intent expired")

    return apply_payment_success(
        db,
        intent,
        external_id=str(external_id),
        raw_payload=json.dumps(payload, ensure_ascii=False)[:8000],
    )


def intent_by_public_token(db: Session, token: str) -> PaymentIntent:
    intent = db.query(PaymentIntent).filter(PaymentIntent.public_token == token).first()
    if not intent:
        raise HTTPException(status_code=404, detail="Payment not found")
    return intent
