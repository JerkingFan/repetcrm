"""Payment intents and webhooks."""

from __future__ import annotations

import json

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.dependencies import get_current_user
from app.models import PaymentIntent, Student, User
from app.schemas import PaymentIntentCreate, PaymentIntentOut, PaymentPublicOut, PaymentWebhookIn
from app.services.payment_service import (
    apply_payment_success,
    create_payment_intent,
    intent_by_public_token,
    process_payment_webhook,
    verify_webhook_signature,
)

router = APIRouter(tags=["payments"])


def _intent_out(intent: PaymentIntent) -> PaymentIntentOut:
    return PaymentIntentOut.model_validate(intent)


@router.post("/payments/intents", response_model=PaymentIntentOut, status_code=201)
def create_intent(
    data: PaymentIntentCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    intent = create_payment_intent(
        db,
        tutor_id=user.id,
        student_id=data.student_id,
        amount=data.amount,
        provider=data.provider,
        purpose=data.purpose,
        purpose_ref_id=data.purpose_ref_id,
    )
    return _intent_out(intent)


@router.get("/payments/intents/{intent_id}", response_model=PaymentIntentOut)
def get_intent(
    intent_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    intent = (
        db.query(PaymentIntent)
        .filter(PaymentIntent.id == intent_id, PaymentIntent.tutor_id == user.id)
        .first()
    )
    if not intent:
        raise HTTPException(status_code=404, detail="Not found")
    return _intent_out(intent)


@router.get("/payments/public/{token}", response_model=PaymentPublicOut)
def get_public_payment(token: str, db: Session = Depends(get_db)):
    intent = (
        db.query(PaymentIntent)
        .options(joinedload(PaymentIntent.student))
        .filter(PaymentIntent.public_token == token)
        .first()
    )
    if not intent:
        raise HTTPException(status_code=404, detail="Payment not found")
    return PaymentPublicOut(
        id=intent.id,
        amount=intent.amount,
        currency=intent.currency,
        provider=intent.provider,
        status=intent.status,
        erip_code=intent.erip_code,
        student_name=intent.student.name if intent.student else "",
        expires_at=intent.expires_at,
    )


@router.post("/payments/public/{token}/simulate-pay", response_model=PaymentIntentOut)
def simulate_public_pay(token: str, db: Session = Depends(get_db)):
    """Dev/demo: confirm payment without external provider."""
    from app.config import get_settings

    if get_settings().app_env == "production":
        raise HTTPException(status_code=403, detail="Not available in production")
    intent = intent_by_public_token(db, token)
    apply_payment_success(
        db,
        intent,
        external_id=f"sim-{intent.id}-{intent.public_token[:8]}",
        raw_payload='{"simulated":true}',
    )
    db.refresh(intent)
    return _intent_out(intent)


@router.post("/webhooks/payments")
async def payment_webhook(
    request: Request,
    db: Session = Depends(get_db),
    x_webhook_signature: str | None = Header(None, alias="X-Webhook-Signature"),
):
    body = await request.body()
    if not verify_webhook_signature(body, x_webhook_signature):
        raise HTTPException(status_code=401, detail="Invalid signature")
    try:
        payload = json.loads(body)
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=400, detail="Invalid JSON") from e
    tx = process_payment_webhook(db, payload)
    return {"ok": True, "transaction_id": tx.id, "status": tx.status}


@router.post("/webhooks/payments/erip", response_model=dict)
async def erip_webhook(
    request: Request,
    db: Session = Depends(get_db),
    x_webhook_signature: str | None = Header(None, alias="X-Webhook-Signature"),
):
    body = await request.body()
    if not verify_webhook_signature(body, x_webhook_signature):
        raise HTTPException(status_code=401, detail="Invalid signature")
    payload = json.loads(body)
    payload.setdefault("status", "paid")
    tx = process_payment_webhook(db, payload)
    return {"ok": True, "transaction_id": tx.id}


@router.post("/webhooks/payments/card", response_model=dict)
async def card_webhook(
    request: Request,
    db: Session = Depends(get_db),
    x_webhook_signature: str | None = Header(None, alias="X-Webhook-Signature"),
):
    body = await request.body()
    if not verify_webhook_signature(body, x_webhook_signature):
        raise HTTPException(status_code=401, detail="Invalid signature")
    payload = json.loads(body)
    tx = process_payment_webhook(db, payload)
    return {"ok": True, "transaction_id": tx.id}
