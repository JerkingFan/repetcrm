"""Parent email notifications."""

import uuid
from datetime import date, timedelta
from unittest.mock import patch

from app.services.reminder_tasks import (
    _send_parent_lesson_tomorrow,
    _send_parent_low_balance,
)


def _register(client):
    email = f"tutor_{uuid.uuid4().hex}@test.example"
    client.post("/auth/register", json={"email": email, "password": "SecurePass99", "name": "Tutor"})


@patch("app.services.parent_notifications.send_email", return_value=True)
def test_parent_lesson_tomorrow_email(mock_send, client):
    _register(client)
    created = client.post(
        "/students",
        json={
            "name": "Kid",
            "subject": "Math",
            "grade": "8",
            "parent_name": "Anna",
            "parent_email": "anna@parent.test",
            "parent_notify_email": True,
        },
    )
    sid = created.json()["id"]
    tomorrow = (date.today() + timedelta(days=1)).isoformat()
    client.post(
        "/lessons",
        json={
            "student_id": sid,
            "lesson_date": tomorrow,
            "lesson_time": "17:00",
            "duration_minutes": 60,
            "payment_amount": 40,
            "is_paid": False,
        },
    )

    from app.database import SessionLocal

    db = SessionLocal()
    try:
        sent = _send_parent_lesson_tomorrow(db)
        db.commit()
    finally:
        db.close()

    assert sent == 1
    mock_send.assert_called_once()
    args, kwargs = mock_send.call_args
    assert kwargs["to"] == "anna@parent.test"
    assert "Завтра" in kwargs["subject"] or "занятие" in kwargs["subject"].lower()
    assert "/parent?token=" in kwargs["body"]


@patch("app.services.parent_notifications.send_email", return_value=True)
def test_parent_low_balance_email(mock_send, client):
    _register(client)
    created = client.post(
        "/students",
        json={
            "name": "Low",
            "subject": "Math",
            "grade": "7",
            "parent_email": "low@parent.test",
            "parent_notify_email": True,
        },
    )
    sid = created.json()["id"]
    client.post(
        f"/students/{sid}/packages",
        json={"name": "4 урока", "lessons_total": 4, "price_per_lesson": 50},
    )

    from app.database import SessionLocal
    from app.models import Student

    db = SessionLocal()
    try:
        student = db.query(Student).filter(Student.id == sid).first()
        assert student is not None
        student.balance = 10.0
        db.flush()
        sent = _send_parent_low_balance(db)
        db.commit()
    finally:
        db.close()

    assert sent == 1
    mock_send.assert_called_once()
    assert mock_send.call_args.kwargs["to"] == "low@parent.test"
    assert "баланс" in mock_send.call_args.kwargs["body"].lower()


@patch("app.services.parent_notifications.send_email", return_value=True)
def test_parent_payment_received_on_webhook(mock_send, client):
    _register(client)
    st = client.post(
        "/students",
        json={
            "name": "PayerKid",
            "subject": "Math",
            "grade": "8",
            "parent_email": "payparent@test.example",
            "parent_notify_email": True,
        },
    )
    sid = st.json()["id"]
    intent = client.post(
        "/payments/intents",
        json={"student_id": sid, "amount": 80, "provider": "card"},
    )
    token = intent.json()["public_token"]

    pay = client.post(f"/payments/public/{token}/simulate-pay")
    assert pay.status_code == 200

    mock_send.assert_called_once()
    assert mock_send.call_args.kwargs["to"] == "payparent@test.example"
    assert "80" in mock_send.call_args.kwargs["body"]


@patch("app.services.parent_notifications.send_email", return_value=True)
def test_parent_notification_skipped_without_email(mock_send, client):
    _register(client)
    created = client.post(
        "/students",
        json={"name": "NoParent", "subject": "Math", "grade": "6", "parent_notify_email": True},
    )
    sid = created.json()["id"]
    tomorrow = (date.today() + timedelta(days=1)).isoformat()
    client.post(
        "/lessons",
        json={
            "student_id": sid,
            "lesson_date": tomorrow,
            "lesson_time": "12:00",
            "duration_minutes": 45,
            "payment_amount": 30,
        },
    )

    from app.database import SessionLocal

    db = SessionLocal()
    try:
        sent = _send_parent_lesson_tomorrow(db)
        db.commit()
    finally:
        db.close()

    assert sent == 0
    mock_send.assert_not_called()
