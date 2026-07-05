"""Manual bank transfer receipts with file proof."""

from __future__ import annotations

import os
import uuid
from datetime import datetime

from fastapi import HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.config import Settings
from app.models import PaymentReceipt, PaymentTransaction, Student

ALLOWED_RECEIPT_MIME = frozenset(
    {"application/pdf", "image/jpeg", "image/png", "image/webp"}
)


async def save_receipt_file(
    cfg: Settings,
    *,
    receipt_id: int,
    file: UploadFile,
) -> tuple[str, str, str]:
    content = await file.read()
    if len(content) > cfg.homework_submission_max_bytes:
        raise HTTPException(status_code=413, detail="File too large")
    mime = (file.content_type or "").split(";")[0].strip().lower()
    if mime not in ALLOWED_RECEIPT_MIME:
        raise HTTPException(status_code=400, detail="Allowed: PDF, JPEG, PNG, WebP")

    sub_dir = os.path.join(cfg.media_dir, "payment_receipts", str(receipt_id))
    os.makedirs(sub_dir, exist_ok=True)
    ext = os.path.splitext(file.filename or "receipt")[1] or ".bin"
    fname = f"{uuid.uuid4().hex}{ext}"
    path = os.path.join(sub_dir, fname)
    with open(path, "wb") as f:
        f.write(content)
    rel_path = os.path.relpath(path, cfg.media_dir).replace("\\", "/")
    return rel_path, mime, file.filename or fname


def create_payment_receipt(
    db: Session,
    *,
    tutor_id: int,
    student_id: int,
    amount: float,
    parent_note: str = "",
) -> PaymentReceipt:
    if amount <= 0:
        raise HTTPException(status_code=400, detail="Сумма должна быть больше 0")
    receipt = PaymentReceipt(
        tutor_id=tutor_id,
        student_id=student_id,
        amount=round(float(amount), 2),
        parent_note=(parent_note or "").strip()[:2000],
        status="pending",
    )
    db.add(receipt)
    db.flush()
    return receipt


def confirm_payment_receipt(db: Session, receipt: PaymentReceipt) -> PaymentTransaction:
    if receipt.status != "pending":
        raise HTTPException(status_code=400, detail="Receipt already reviewed")

    existing = (
        db.query(PaymentTransaction)
        .filter(
            PaymentTransaction.provider == "manual_receipt",
            PaymentTransaction.external_id == f"receipt-{receipt.id}",
        )
        .first()
    )
    if existing:
        return existing

    now = datetime.utcnow()
    receipt.status = "confirmed"
    receipt.reviewed_at = now

    student = db.query(Student).filter(Student.id == receipt.student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    student.balance = round(float(student.balance or 0) + receipt.amount, 2)

    tx = PaymentTransaction(
        intent_id=None,
        tutor_id=receipt.tutor_id,
        student_id=receipt.student_id,
        amount=receipt.amount,
        currency="BYN",
        provider="manual_receipt",
        external_id=f"receipt-{receipt.id}",
        status="paid",
        raw_payload=f'{{"receipt_id":{receipt.id}}}',
    )
    db.add(tx)
    db.flush()
    return tx


def reject_payment_receipt(db: Session, receipt: PaymentReceipt, *, tutor_note: str = "") -> None:
    if receipt.status != "pending":
        raise HTTPException(status_code=400, detail="Receipt already reviewed")
    receipt.status = "rejected"
    receipt.tutor_note = (tutor_note or "").strip()[:2000]
    receipt.reviewed_at = datetime.utcnow()
