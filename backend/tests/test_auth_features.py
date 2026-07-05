"""Password reset, change password, notifications settings, recurring lessons."""

from datetime import date, timedelta

from sqlalchemy.orm import Session

from app.models import PasswordResetToken, User
from app.services.password_reset import create_reset_token


def _register(client, email: str = "tutor@test.example", password: str = "SecurePass99"):
    r = client.post(
        "/auth/register",
        json={"email": email, "password": password, "name": "Tutor"},
    )
    assert r.status_code == 200, r.text


def _create_student(client, name: str = "Alice"):
    r = client.post(
        "/students",
        json={"name": name, "subject": "Math", "grade": "9"},
    )
    assert r.status_code == 201, r.text
    return r.json()["id"]


def _db_session(client) -> Session:
    from app.database import get_db

    override = client.app.dependency_overrides.get(get_db)
    assert override is not None, "get_db override missing — conftest must register test DB"
    gen = override()
    return next(gen)


def test_forgot_password_always_ok(client):
    _register(client)
    assert client.post("/auth/forgot-password", json={"email": "tutor@test.example"}).status_code == 200
    assert client.post("/auth/forgot-password", json={"email": "nobody@test.example"}).status_code == 200

    db = _db_session(client)
    user = db.query(User).filter(User.email == "tutor@test.example").first()
    assert db.query(PasswordResetToken).filter(PasswordResetToken.user_id == user.id).count() >= 1


def test_reset_and_change_password(client):
    _register(client)
    db = _db_session(client)
    user = db.query(User).filter(User.email == "tutor@test.example").first()
    raw = create_reset_token(db, user)
    db.commit()

    reset = client.post(
        "/auth/reset-password",
        json={"token": raw, "password": "NewSecurePass1"},
    )
    assert reset.status_code == 200, reset.text

    assert (
        client.post("/auth/login", json={"email": "tutor@test.example", "password": "SecurePass99"}).status_code
        == 401
    )
    assert (
        client.post("/auth/login", json={"email": "tutor@test.example", "password": "NewSecurePass1"}).status_code
        == 200
    )

    assert (
        client.post(
            "/auth/change-password",
            json={"current_password": "NewSecurePass1", "new_password": "AnotherSecure1"},
        ).status_code
        == 200
    )
    assert (
        client.post(
            "/auth/change-password",
            json={"current_password": "wrong", "new_password": "AnotherSecure2"},
        ).status_code
        == 400
    )


def test_notification_settings(client):
    _register(client)
    r = client.get("/auth/notification-settings")
    assert r.status_code == 200
    data = r.json()
    assert data["notify_email"] is True
    assert "smtp_configured" in data

    upd = client.put(
        "/auth/notification-settings",
        json={
            "notify_telegram": True,
            "telegram_chat_id": "12345",
            "notify_unpaid": False,
        },
    )
    assert upd.status_code == 200
    assert upd.json()["notify_unpaid"] is False
    assert upd.json()["telegram_chat_id"] == "12345"


def test_recurring_lesson_create(client):
    _register(client)
    sid = _create_student(client)

    today = date.today()
    days_ahead = (1 - today.weekday()) % 7 or 7
    lesson_date = (today + timedelta(days=days_ahead)).isoformat()

    r = client.post(
        "/lessons",
        json={
            "student_id": sid,
            "lesson_date": lesson_date,
            "lesson_time": "17:00",
            "duration_minutes": 60,
            "payment_amount": 50,
            "is_paid": False,
            "notes": "",
            "recurrence": {"weekday": 1, "weeks_ahead": 4},
        },
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["series"] is not None
    assert body["series"]["lessons_created"] >= 4
    assert body["lesson"]["series_id"] is not None
    assert len(client.get("/lessons").json()) >= 4
