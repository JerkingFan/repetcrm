"""Student portal v2: meeting links, due dates, progress, reschedule."""

import io
import uuid
from datetime import date, timedelta


def _register(client, password: str = "SecurePass99"):
    email = f"tutor_{uuid.uuid4().hex}@test.example"
    client.post("/auth/register", json={"email": email, "password": password, "name": "Tutor"})


def _create_student(client, name: str = "Student"):
    r = client.post("/students", json={"name": name, "subject": "Math", "grade": "7"})
    assert r.status_code == 201, r.text
    return r.json()["id"]


def test_portal_session_and_schedule(client):
    _register(client)
    sid = _create_student(client, "Eve")
    link = client.get(f"/students/{sid}/portal-link")
    assert link.status_code == 200
    token = link.json()["portal_token"]

    session = client.post("/portal/session", json={"portal_token": token})
    assert session.status_code == 200
    assert session.json()["name"] == "Eve"

    me = client.get("/portal/me")
    assert me.status_code == 200

    client.post(
        "/lessons",
        json={
            "student_id": sid,
            "lesson_date": (date.today() + timedelta(days=2)).isoformat(),
            "lesson_time": "11:00",
            "duration_minutes": 60,
            "payment_amount": 40,
            "is_paid": False,
            "meeting_url": "https://meet.example.com/room-1",
        },
    )
    lessons = client.get("/portal/lessons")
    assert lessons.status_code == 200
    assert len(lessons.json()) >= 1
    assert lessons.json()[0]["meeting_url"] == "https://meet.example.com/room-1"


def test_portal_progress_and_hide_balance(client):
    _register(client)
    sid = _create_student(client, "ProgressKid")
    token = client.get(f"/students/{sid}/portal-link").json()["portal_token"]
    client.post("/portal/session", json={"portal_token": token})

    client.put(
        "/auth/notification-settings",
        json={
            "contact_telegram": "test_tutor",
            "hide_balance_in_portal": True,
        },
    )
    me = client.get("/portal/me")
    assert me.status_code == 200
    assert me.json()["show_balance"] is False
    assert "t.me/test_tutor" in me.json()["tutor_telegram_url"]

    progress = client.get("/portal/progress")
    assert progress.status_code == 200
    body = progress.json()
    assert "homework_total" in body
    assert "streak_days" in body


def test_portal_reschedule_request(client):
    _register(client)
    sid = _create_student(client, "Resched")
    token = client.get(f"/students/{sid}/portal-link").json()["portal_token"]
    client.post("/portal/session", json={"portal_token": token})

    lesson_date = (date.today() + timedelta(days=5)).isoformat()
    preferred = (date.today() + timedelta(days=8)).isoformat()
    lesson = client.post(
        "/lessons",
        json={
            "student_id": sid,
            "lesson_date": lesson_date,
            "lesson_time": "12:00",
            "duration_minutes": 60,
            "payment_amount": 0,
            "is_paid": True,
        },
    ).json()["lesson"]
    lid = lesson["id"]

    req = client.post(
        "/portal/reschedule",
        json={
            "lesson_id": lid,
            "message": "Не могу в этот день",
            "preferred_date": preferred,
            "preferred_time": "14:00",
        },
    )
    assert req.status_code == 201
    assert req.json()["status"] == "pending"

    pending = client.get("/reschedule-requests?status=pending")
    assert pending.status_code == 200
    items = pending.json()
    assert len(items) >= 1
    rid = items[0]["id"]

    resolved = client.post(
        f"/reschedule-requests/{rid}/resolve",
        json={"status": "approved", "tutor_note": "Ок"},
    )
    assert resolved.status_code == 200

    updated_lesson = client.get(f"/lessons/{lid}")
    assert updated_lesson.status_code == 200
    assert updated_lesson.json()["lesson_date"] == preferred
    assert updated_lesson.json()["lesson_time"].startswith("14:00")


def test_homework_due_date_on_generate(client):
    _register(client)
    sid = _create_student(client, "DueKid")
    next_date = (date.today() + timedelta(days=7)).isoformat()
    client.post(
        "/lessons",
        json={
            "student_id": sid,
            "lesson_date": next_date,
            "lesson_time": "10:00",
            "duration_minutes": 60,
            "payment_amount": 0,
            "is_paid": True,
        },
    )
    lesson_res = client.post(
        "/lessons",
        json={
            "student_id": sid,
            "lesson_date": date.today().isoformat(),
            "lesson_time": "10:00",
            "duration_minutes": 60,
            "payment_amount": 0,
            "is_paid": True,
        },
    )
    lid = lesson_res.json()["lesson"]["id"]
    client.post(
        f"/lessons/{lid}/lesson-report",
        json={
            "is_conducted": True,
            "items": [{"topic": "Algebra", "work_type": "practice", "difficulty": "medium", "understanding": 3}],
            "prefs": {},
        },
    )
    gen = client.post(f"/lessons/{lid}/generate-homework")
    assert gen.status_code == 200, gen.text
    assert gen.json().get("due_date") == next_date


def test_lesson_package_and_auto_pay(client):
    _register(client)
    sid = _create_student(client, "Frank")
    pkg = client.post(
        f"/students/{sid}/packages",
        json={"name": "8 занятий", "lessons_total": 8, "price_per_lesson": 40},
    )
    assert pkg.status_code == 201
    assert pkg.json()["lessons_remaining"] == 8

    lesson_res = client.post(
        "/lessons",
        json={
            "student_id": sid,
            "lesson_date": date.today().isoformat(),
            "lesson_time": "15:00",
            "duration_minutes": 60,
            "payment_amount": 40,
            "is_paid": False,
        },
    )
    assert lesson_res.status_code == 201
    lid = lesson_res.json()["lesson"]["id"]

    report = client.post(
        f"/lessons/{lid}/lesson-report",
        json={
            "is_conducted": True,
            "items": [{"topic": "Test", "work_type": "practice", "difficulty": "medium", "understanding": 3}],
            "prefs": {},
        },
    )
    assert report.status_code == 200
    assert report.json()["is_paid"] is True

    packages = client.get(f"/students/{sid}/packages")
    assert packages.json()[0]["lessons_remaining"] == 7


def test_calendar_ics_feed(client):
    _register(client)
    sid = _create_student(client, "Grace")
    token = client.get(f"/students/{sid}/portal-link").json()["portal_token"]
    client.post(
        "/lessons",
        json={
            "student_id": sid,
            "lesson_date": (date.today() + timedelta(days=1)).isoformat(),
            "lesson_time": "09:00",
            "duration_minutes": 45,
            "payment_amount": 0,
            "is_paid": True,
            "meeting_url": "https://zoom.example/j/123",
        },
    )
    ics = client.get(f"/calendar/feed.ics?token={token}")
    assert ics.status_code == 200
    assert b"BEGIN:VCALENDAR" in ics.content
    assert b"zoom.example" in ics.content

    tutor_ics = client.get("/calendar/tutor.ics")
    assert tutor_ics.status_code == 200
    assert b"BEGIN:VCALENDAR" in tutor_ics.content


def test_portal_homework_submit(client):
    _register(client)
    sid = _create_student(client, "Hank")
    token_resp = client.get(f"/students/{sid}/portal-link")
    assert token_resp.status_code == 200, token_resp.text
    token = token_resp.json()["portal_token"]
    login = client.post("/portal/session", json={"portal_token": token})
    assert login.status_code == 200, login.text

    lesson_res = client.post(
        "/lessons",
        json={
            "student_id": sid,
            "lesson_date": date.today().isoformat(),
            "lesson_time": "16:00",
            "duration_minutes": 45,
            "payment_amount": 0,
            "is_paid": True,
        },
    )
    assert lesson_res.status_code == 201
    lesson_id = lesson_res.json()["lesson"]["id"]

    client.post(
        f"/lessons/{lesson_id}/lesson-report",
        json={
            "is_conducted": True,
            "items": [{"topic": "HW test", "work_type": "practice", "difficulty": "medium", "understanding": 3}],
            "prefs": {},
        },
    )
    gen = client.post(f"/lessons/{lesson_id}/generate-homework")
    assert gen.status_code == 200, gen.text
    hw_id = gen.json()["id"]

    hw_list = client.get("/portal/homework")
    assert hw_list.status_code == 200
    assert any(h["id"] == hw_id for h in hw_list.json())

    pdf_bytes = b"%PDF-1.4 test"
    files = {"file": ("answer.pdf", io.BytesIO(pdf_bytes), "application/pdf")}
    sub = client.post(f"/portal/homework/{hw_id}/submit", files=files, data={"comment": "Done"})
    assert sub.status_code == 200
    assert sub.json()["original_filename"] == "answer.pdf"
