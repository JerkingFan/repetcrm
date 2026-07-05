"""Public trial lesson booking."""

import uuid
from unittest.mock import patch

from app.schemas import BookingHoursSlot
from app.services.booking_service import dump_booking_hours


def _register(client, name: str = "Tutor"):
    email = f"tutor_{uuid.uuid4().hex}@test.example"
    client.post("/auth/register", json={"email": email, "password": "SecurePass99", "name": name})
    return email


def _enable_booking(client, slug: str):
    res = client.put(
        "/book/settings/me",
        json={
            "booking_slug": slug,
            "booking_enabled": True,
            "booking_hours": [BookingHoursSlot(weekday=d).model_dump() for d in range(5)],
        },
    )
    assert res.status_code == 200, res.text
    return res.json()


def test_booking_settings_and_public_page(client):
    _register(client, "Anna Tutor")
    slug = f"anna-{uuid.uuid4().hex[:8]}"
    settings = _enable_booking(client, slug)
    assert settings["booking_enabled"] is True
    assert slug in settings["booking_url"]

    public = client.get(f"/book/{slug}")
    assert public.status_code == 200
    body = public.json()
    assert body["tutor_name"] == "Anna Tutor"
    assert len(body["slots"]) > 0

    disabled = client.get("/book/not-enabled-slug")
    assert disabled.status_code == 404


@patch("app.services.booking_notifications.send_email", return_value=True)
def test_submit_trial_booking_creates_lead(mock_send, client):
    _register(client, "Book Tutor")
    slug = f"book-{uuid.uuid4().hex[:8]}"
    _enable_booking(client, slug)

    public = client.get(f"/book/{slug}").json()
    slot = public["slots"][0]

    created = client.post(
        f"/book/{slug}",
        json={
            "child_name": "Masha",
            "grade": "7",
            "subject": "Math",
            "parent_name": "Olga",
            "parent_email": "olga@parent.test",
            "parent_phone": "+375291111111",
            "preferred_date": slot["date"],
            "preferred_time": slot["time"],
            "message": "Хотим онлайн",
        },
    )
    assert created.status_code == 201, created.text
    assert created.json()["booking_id"] > 0

    leads = client.get("/book/leads/me")
    assert leads.status_code == 200
    items = leads.json()
    assert len(items) == 1
    assert items[0]["child_name"] == "Masha"
    assert items[0]["status"] == "new"

    student = client.get(f"/students/{items[0]['student_id']}")
    assert student.status_code == 200

    assert mock_send.call_count >= 1


def test_booking_rejects_busy_slot(client):
    _register(client)
    slug = f"busy-{uuid.uuid4().hex[:8]}"
    _enable_booking(client, slug)

    sid = client.post(
        "/students",
        json={"name": "Existing", "subject": "Math", "grade": "8"},
    ).json()["id"]

    slot = client.get(f"/book/{slug}").json()["slots"][0]
    client.post(
        "/lessons",
        json={
            "student_id": sid,
            "lesson_date": slot["date"],
            "lesson_time": slot["time"],
            "duration_minutes": 60,
            "payment_amount": 0,
            "is_paid": False,
        },
    )

    dup = client.post(
        f"/book/{slug}",
        json={
            "child_name": "Kid",
            "grade": "7",
            "subject": "Math",
            "parent_name": "Parent",
            "parent_email": "p@test.example",
            "preferred_date": slot["date"],
            "preferred_time": slot["time"],
        },
    )
    assert dup.status_code == 400


def test_update_lead_status(client):
    _register(client)
    slug = f"lead-{uuid.uuid4().hex[:8]}"
    _enable_booking(client, slug)
    slot = client.get(f"/book/{slug}").json()["slots"][0]

    with patch("app.services.booking_notifications.send_email", return_value=True):
        client.post(
            f"/book/{slug}",
            json={
                "child_name": "Kid",
                "grade": "6",
                "subject": "Math",
                "parent_name": "Mom",
                "parent_email": "mom@test.example",
                "preferred_date": slot["date"],
                "preferred_time": slot["time"],
            },
        )

    lead_id = client.get("/book/leads/me").json()[0]["id"]
    updated = client.patch(f"/book/leads/{lead_id}?status=contacted")
    assert updated.status_code == 200
    assert updated.json()["status"] == "contacted"
