"""Manual payment receipts (bank transfer + proof file)."""

from __future__ import annotations

import os

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session, joinedload

from app.config import get_settings
from app.database import get_db
from app.dependencies import get_current_user
from app.models import PaymentReceipt, Student, User
from app.schemas import MessageOut, PaymentReceiptOut, PaymentReceiptReviewIn
from app.services.dashboard_cache import invalidate_dashboard
from app.services.manual_payment_service import (
    confirm_payment_receipt,
    reject_payment_receipt,
)

router = APIRouter(prefix="/payments/receipts", tags=["payments"])


def _receipt_out(receipt: PaymentReceipt, student_name: str = "") -> PaymentReceiptOut:
    return PaymentReceiptOut(
        id=receipt.id,
        student_id=receipt.student_id,
        student_name=student_name or (receipt.student.name if receipt.student else ""),
        amount=float(receipt.amount),
        status=receipt.status,
        original_filename=receipt.original_filename,
        parent_note=receipt.parent_note or "",
        tutor_note=receipt.tutor_note or "",
        created_at=receipt.created_at,
        reviewed_at=receipt.reviewed_at,
    )


def _receipt_file_path(receipt: PaymentReceipt) -> str:
    cfg = get_settings()
    if not receipt.file_path:
        raise HTTPException(status_code=404, detail="File not found")
    path = os.path.join(cfg.media_dir, receipt.file_path.replace("/", os.sep))
    if not os.path.isfile(path):
        raise HTTPException(status_code=404, detail="File not found")
    return path


@router.get("", response_model=list[PaymentReceiptOut])
def list_payment_receipts(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    status: str | None = Query(None, description="pending|confirmed|rejected"),
    student_id: int | None = Query(None),
):
    q = (
        db.query(PaymentReceipt)
        .options(joinedload(PaymentReceipt.student))
        .filter(PaymentReceipt.tutor_id == user.id)
    )
    if status:
        q = q.filter(PaymentReceipt.status == status.strip().lower())
    if student_id is not None:
        q = q.filter(PaymentReceipt.student_id == student_id)
    rows = q.order_by(PaymentReceipt.created_at.desc()).limit(50).all()
    return [_receipt_out(r) for r in rows]


@router.get("/{receipt_id}", response_model=PaymentReceiptOut)
def get_payment_receipt(
    receipt_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    receipt = (
        db.query(PaymentReceipt)
        .options(joinedload(PaymentReceipt.student))
        .filter(PaymentReceipt.id == receipt_id, PaymentReceipt.tutor_id == user.id)
        .first()
    )
    if not receipt:
        raise HTTPException(status_code=404, detail="Not found")
    return _receipt_out(receipt)


@router.get("/{receipt_id}/file")
def download_payment_receipt_file(
    receipt_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    receipt = (
        db.query(PaymentReceipt)
        .filter(PaymentReceipt.id == receipt_id, PaymentReceipt.tutor_id == user.id)
        .first()
    )
    if not receipt:
        raise HTTPException(status_code=404, detail="Not found")
    path = _receipt_file_path(receipt)
    return FileResponse(path, media_type=receipt.mime_type, filename=receipt.original_filename)


@router.post("/{receipt_id}/confirm", response_model=PaymentReceiptOut)
def confirm_receipt(
    receipt_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    receipt = (
        db.query(PaymentReceipt)
        .options(joinedload(PaymentReceipt.student))
        .filter(PaymentReceipt.id == receipt_id, PaymentReceipt.tutor_id == user.id)
        .first()
    )
    if not receipt:
        raise HTTPException(status_code=404, detail="Not found")
    confirm_payment_receipt(db, receipt)
    db.commit()
    invalidate_dashboard(user.id)
    db.refresh(receipt)
    return _receipt_out(receipt)


@router.post("/{receipt_id}/reject", response_model=PaymentReceiptOut)
def reject_receipt(
    receipt_id: int,
    data: PaymentReceiptReviewIn,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    receipt = (
        db.query(PaymentReceipt)
        .options(joinedload(PaymentReceipt.student))
        .filter(PaymentReceipt.id == receipt_id, PaymentReceipt.tutor_id == user.id)
        .first()
    )
    if not receipt:
        raise HTTPException(status_code=404, detail="Not found")
    reject_payment_receipt(db, receipt, tutor_note=data.tutor_note)
    db.commit()
    invalidate_dashboard(user.id)
    db.refresh(receipt)
    return _receipt_out(receipt)
