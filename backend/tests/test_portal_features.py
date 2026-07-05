"""Student portal, packages, calendar ICS."""

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
        },
    )
    lessons = client.get("/portal/lessons")
    assert lessons.status_code == 200
    assert len(lessons.json()) >= 1


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
    ics = client.get(f"/calendar/feed.ics?token={token}")
    assert ics.status_code == 200
    assert b"BEGIN:VCALENDAR" in ics.content

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

    pdf_bytes = b"%PDF-1.4 test"
    files = {"file": ("answer.pdf", io.BytesIO(pdf_bytes), "application/pdf")}
    sub = client.post(f"/portal/homework/{hw_id}/submit", files=files, data={"comment": "Done"})
    assert sub.status_code == 200
    assert sub.json()["original_filename"] == "answer.pdf"

