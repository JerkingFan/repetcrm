"""AI homework submission review."""

import io
import json
from datetime import date
from unittest.mock import AsyncMock, patch

from tests.test_portal_features import _create_student, _register


def _lesson_with_homework(client, sid: int) -> tuple[int, int]:
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
    assert lesson_res.status_code == 201, lesson_res.text
    lid = lesson_res.json()["lesson"]["id"]
    client.post(
        f"/lessons/{lid}/lesson-report",
        json={
            "is_conducted": True,
            "items": [{"topic": "HW", "work_type": "practice", "difficulty": "medium", "understanding": 3}],
            "prefs": {},
        },
    )
    gen = client.post(f"/lessons/{lid}/generate-homework")
    assert gen.status_code == 200, gen.text
    return lid, gen.json()["id"]


@patch("app.routers.portal.schedule_ai_review")
@patch(
    "app.services.homework_submission_ai.call_openrouter_vision",
    new_callable=AsyncMock,
)
def test_ai_review_after_photo_submit(mock_vision, mock_schedule, client):
    mock_vision.return_value = json.dumps(
        {
            "verdict": "correct",
            "score": 92,
            "feedback": "Отлично решено, все шаги верные.",
        }
    )

    _register(client)
    sid = _create_student(client, "AIStudent")
    _, hw_id = _lesson_with_homework(client, sid)

    token = client.get(f"/students/{sid}/portal-link").json()["portal_token"]
    client.post("/portal/session", json={"portal_token": token})

    png = b"\x89PNG\r\n\x1a\n" + b"\x00" * 64
    submit = client.post(
        f"/portal/homework/{hw_id}/submit",
        files={"file": ("solution.png", io.BytesIO(png), "image/png")},
        data={"comment": "задача 3"},
    )
    assert submit.status_code == 200
    body = submit.json()
    assert body["ai_review_status"] == "pending"

    import asyncio
    from app.services.homework_submission_ai import review_submission_ai

    asyncio.run(review_submission_ai(body["id"]))

    detail = client.get(f"/portal/homework/{hw_id}").json()
    latest = detail["submissions"][0]
    assert latest["ai_review_status"] == "done"
    assert latest["ai_verdict"] == "correct"
    assert latest["ai_score"] == 92
    assert "Отлично" in latest["ai_feedback"]
    mock_vision.assert_awaited_once()


def test_ai_review_skipped_for_pdf(client):
    _register(client)
    sid = _create_student(client, "PDFStudent")
    _, hw_id = _lesson_with_homework(client, sid)

    token = client.get(f"/students/{sid}/portal-link").json()["portal_token"]
    client.post("/portal/session", json={"portal_token": token})

    submit = client.post(
        f"/portal/homework/{hw_id}/submit",
        files={"file": ("answer.pdf", io.BytesIO(b"%PDF-1.4 test"), "application/pdf")},
    )
    assert submit.status_code == 200
    body = submit.json()
    assert body["ai_review_status"] == "skipped"
    assert "фото" in body["ai_feedback"].lower()
