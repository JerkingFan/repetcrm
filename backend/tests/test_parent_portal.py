"""Parent portal and structured parent contacts."""

import uuid
from datetime import date, timedelta


def _register(client, password: str = "SecurePass99"):
    email = f"tutor_{uuid.uuid4().hex}@test.example"
    client.post("/auth/register", json={"email": email, "password": password, "name": "Tutor"})


def test_student_parent_fields_crud(client):
    _register(client)
    created = client.post(
        "/students",
        json={
            "name": "Kid",
            "subject": "Math",
            "grade": "8",
            "parent_name": "Anna Parent",
            "parent_email": "anna@parent.test",
            "parent_phone": "+375291234567",
            "parent_notify_email": True,
        },
    )
    assert created.status_code == 201, created.text
    body = created.json()
    assert body["parent_name"] == "Anna Parent"
    assert body["parent_email"] == "anna@parent.test"
    assert "anna@parent.test" in body["parent_contact"]

    sid = body["id"]
    updated = client.put(
        f"/students/{sid}",
        json={"parent_phone": "+375299999999"},
    )
    assert updated.status_code == 200
    assert updated.json()["parent_phone"] == "+375299999999"


def test_parent_portal_session_schedule_and_payment(client):
    _register(client)
    created = client.post(
        "/students",
        json={
            "name": "Leo",
            "subject": "Physics",
            "grade": "9",
            "parent_name": "Mom",
            "parent_email": "mom@test.example",
        },
    )
    sid = created.json()["id"]
    link = client.get(f"/students/{sid}/parent-portal-link")
    assert link.status_code == 200
    token = link.json()["parent_portal_token"]
    assert "/parent?token=" in link.json()["parent_portal_url"]

    session = client.post("/parent-portal/session", json={"parent_portal_token": token})
    assert session.status_code == 200
    assert session.json()["student_name"] == "Leo"
    assert session.json()["parent_name"] == "Mom"

    me = client.get("/parent-portal/me")
    assert me.status_code == 200

    client.post(
        "/lessons",
        json={
            "student_id": sid,
            "lesson_date": (date.today() + timedelta(days=3)).isoformat(),
            "lesson_time": "14:00",
            "duration_minutes": 60,
            "payment_amount": 50,
            "is_paid": False,
        },
    )
    lessons = client.get("/parent-portal/lessons")
    assert lessons.status_code == 200
    assert len(lessons.json()) >= 1

    intent = client.post(
        "/parent-portal/payments/intent",
        json={"amount": 100, "provider": "card"},
    )
    assert intent.status_code == 201
    assert intent.json()["payment_url"]


def test_parent_portal_calendar_ics_and_feed_token(client):
    _register(client)
    sid = client.post(
        "/students",
        json={"name": "Mia", "subject": "Math", "grade": "7"},
    ).json()["id"]
    token = client.get(f"/students/{sid}/parent-portal-link").json()["parent_portal_token"]
    client.post("/parent-portal/session", json={"parent_portal_token": token})

    ics = client.get("/parent-portal/calendar.ics")
    assert ics.status_code == 200
    assert b"BEGIN:VCALENDAR" in ics.content

    feed = client.get(f"/calendar/feed.ics?token={token}")
    assert feed.status_code == 200
    assert b"BEGIN:VCALENDAR" in feed.content
