"""Homework template save and apply."""

import uuid


def _register(client, password: str = "SecurePass99"):
    email = f"tpl_{uuid.uuid4().hex}@test.example"
    client.post("/auth/register", json={"email": email, "password": password, "name": "Tutor Tpl"})


def test_homework_template_from_lesson_and_apply(client):
    _register(client)

    st = client.post("/students", json={"name": "Tpl Student", "subject": "Math", "grade": "8"})
    assert st.status_code == 201
    student_id = st.json()["id"]

    lesson = client.post(
        "/lessons",
        json={
            "student_id": student_id,
            "lesson_date": "2026-07-10",
            "lesson_time": "14:00",
            "duration_minutes": 60,
            "payment_amount": 40,
        },
    )
    assert lesson.status_code == 201
    lesson_id = lesson.json()["lesson"]["id"]

    report = client.post(
        f"/lessons/{lesson_id}/lesson-report",
        json={
            "items": [
                {
                    "topic": "Дроби",
                    "work_type": "practice",
                    "difficulty": "medium",
                    "understanding": 4,
                }
            ],
            "prefs": {"focus_aspect": "practice", "volume": "standard"},
            "is_conducted": True,
        },
    )
    assert report.status_code == 200

    hw = client.post(f"/lessons/{lesson_id}/generate-homework")
    assert hw.status_code == 200
    homework_text = hw.json()["homework_text"]
    assert homework_text

    tpl = client.post(
        f"/homework-templates/from-lesson/{lesson_id}",
        json={"name": "Дроби 8 класс", "include_homework_text": True},
    )
    assert tpl.status_code == 201
    template_id = tpl.json()["id"]
    assert tpl.json()["name"] == "Дроби 8 класс"
    assert tpl.json()["preview"]

    lesson2 = client.post(
        "/lessons",
        json={
            "student_id": student_id,
            "lesson_date": "2026-07-17",
            "lesson_time": "15:00",
            "duration_minutes": 60,
        },
    )
    lesson2_id = lesson2.json()["lesson"]["id"]

    applied = client.post(
        f"/homework-templates/{template_id}/apply-to-lesson/{lesson2_id}",
        json={"copy_homework_text": True},
    )
    assert applied.status_code == 200
    assert len(applied.json()["checklist_items"]) == 1
    assert applied.json()["checklist_items"][0]["topic"] == "Дроби"
    assert applied.json()["homework"]["homework_text"] == homework_text

    listed = client.get("/homework-templates")
    assert listed.status_code == 200
    assert any(t["id"] == template_id for t in listed.json())
