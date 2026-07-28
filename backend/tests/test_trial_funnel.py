"""Trial funnel: dashboard widgets and follow-up messages."""

import uuid
from datetime import date, timedelta
from unittest.mock import patch

from app.schemas import BookingHoursSlot
from app.services.trial_funnel_service import week_bounds


def _register(client, name: str = "Tutor"):
    email = f"tutor_{uuid.uuid4().hex}@test.example"
    client.post("/auth/register", json={"email": email, "password": "SecurePass99", "name": name})


def _lead_student(client, slug_prefix: str, child_name: str = "Trial Kid") -> int:
    slug = f"{slug_prefix}-{uuid.uuid4().hex[:8]}"
    client.put(
        "/book/settings/me",
        json={
            "booking_slug": slug,
            "booking_enabled": True,
            "booking_hours": [BookingHoursSlot(weekday=d).model_dump() for d in range(5)],
        },
    )
    slot = client.get(f"/book/{slug}").json()["slots"][0]
    with patch("app.services.booking_notifications.send_email", return_value=True):
        client.post(
            f"/book/{slug}",
            json={
                "child_name": child_name,
                "grade": "8",
                "subject": "Math",
                "parent_name": "Mom",
                "parent_email": "mom@test.example",
                "preferred_date": slot["date"],
                "preferred_time": slot["time"],
            },
        )
    return client.get("/book/leads/me").json()[0]["student_id"]


def test_tutor_can_schedule_manual_trial_lesson(client):
    """Tutor marks a regular student lesson as trial — enters funnel without public booking."""
    _register(client)
    sid = client.post(
        "/students",
        json={"name": "Offline Trial", "subject": "Math", "grade": "7"},
    ).json()["id"]

    week_start, week_end = week_bounds(date.today())
    lesson_date = week_start.isoformat()
    if week_start > week_end:
        lesson_date = date.today().isoformat()

    res = client.post(
        "/lessons",
        json={
            "student_id": sid,
            "lesson_date": lesson_date,
            "lesson_time": "12:00",
            "duration_minutes": 60,
            "payment_amount": 0,
            "is_paid": False,
            "is_trial": True,
        },
    )
    assert res.status_code == 201, res.text

    # Recurrence + trial must be rejected
    bad = client.post(
        "/lessons",
        json={
            "student_id": sid,
            "lesson_date": date.today().isoformat(),
            "lesson_time": "13:00",
            "duration_minutes": 60,
            "is_trial": True,
            "recurrence": {"weekday": date.today().weekday(), "weeks_ahead": 4},
        },
    )
    assert bad.status_code == 400

    dash = client.get("/dashboard/extended")
    assert dash.status_code == 200
    trials = dash.json()["trial_lessons_this_week"]
    assert any(t["student_id"] == sid for t in trials)

    leads = client.get("/book/leads/me").json()
    assert any(l["student_id"] == sid and l["status"] == "scheduled" for l in leads)


def test_quick_conduct_and_followup_message(client):
    _register(client, "Follow Tutor")
    sid = _lead_student(client, "fol")

    lid = client.post(
        "/lessons",
        json={
            "student_id": sid,
            "lesson_date": date.today().isoformat(),
            "lesson_time": "14:00",
            "duration_minutes": 60,
            "payment_amount": 50,
            "is_paid": False,
        },
    ).json()["lesson"]["id"]

    res = client.post(f"/lessons/{lid}/quick-conduct")
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["is_conducted"] is True
    assert body["trial_followup"] is not None
    assert body["trial_followup"]["show"] is True
    assert "/parent?token=" in body["trial_followup"]["message"]

    followup = client.get(f"/students/{sid}/trial-followup")
    assert followup.status_code == 200
    assert followup.json()["show"] is True

    dash = client.get("/dashboard/extended")
    assert any(f["student_id"] == sid for f in dash.json()["trial_followups"])


def test_lead_becomes_trial_after_first_lesson(client):
    _register(client)
    student_id = _lead_student(client, "lead", "Lead Kid")

    lid = client.post(
        "/lessons",
        json={
            "student_id": student_id,
            "lesson_date": date.today().isoformat(),
            "lesson_time": "16:00",
            "duration_minutes": 45,
            "payment_amount": 0,
            "is_paid": True,
        },
    ).json()["lesson"]["id"]
    client.post(f"/lessons/{lid}/quick-conduct")

    from app.database import SessionLocal
    from app.models import Student

    db = SessionLocal()
    try:
        student = db.query(Student).filter(Student.id == student_id).first()
        assert student.student_status == "trial"
    finally:
        db.close()


def test_followup_hidden_after_second_lesson(client):
    _register(client)
    sid = _lead_student(client, "hid", "Two Lessons")
    for i, t in enumerate(["10:00", "12:00"]):
        lid = client.post(
            "/lessons",
            json={
                "student_id": sid,
                "lesson_date": (date.today() - timedelta(days=7 - i)).isoformat(),
                "lesson_time": t,
                "duration_minutes": 60,
                "payment_amount": 40,
                "is_paid": True,
            },
        ).json()["lesson"]["id"]
        client.post(f"/lessons/{lid}/quick-conduct")

    followup = client.get(f"/students/{sid}/trial-followup")
    assert followup.json()["show"] is False
