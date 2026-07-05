"""Homework submission review workflow."""

import io
import uuid
from datetime import date
from unittest.mock import patch

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


@patch("app.services.parent_notifications.send_email", return_value=True)
def test_review_submission_and_parent_status(mock_send, client):
    _register(client)
    sid = _create_student(client, "Reviewer")
    client.put(
        f"/students/{sid}",
        json={
            "parent_name": "Parent",
            "parent_email": "parent-hw@test.example",
            "parent_notify_email": True,
        },
    )

    _, hw_id = _lesson_with_homework(client, sid)

    token = client.get(f"/students/{sid}/portal-link").json()["portal_token"]
    client.post("/portal/session", json={"portal_token": token})
    files = {"file": ("answer.pdf", io.BytesIO(b"%PDF-1.4 test"), "application/pdf")}
    submit = client.post(f"/portal/homework/{hw_id}/submit", files=files, data={"comment": "done"})
    assert submit.status_code == 200
    assert submit.json()["status"] == "submitted"

    sub_id = client.get(f"/homework/{hw_id}/submissions").json()[0]["id"]
    review = client.post(
        f"/homework/{hw_id}/submissions/{sub_id}/review",
        json={"status": "reviewed", "tutor_comment": "Отлично!"},
    )
    assert review.status_code == 200
    assert review.json()["status"] == "reviewed"

    parent_token = client.get(f"/students/{sid}/parent-portal-link").json()["parent_portal_token"]
    client.post("/parent-portal/session", json={"parent_portal_token": parent_token})
    status = client.get("/parent-portal/homework-status")
    row = next(r for r in status.json() if r["homework_id"] == hw_id)
    assert row["status"] == "reviewed"
    assert row["status_label"] == "Проверено"

    mock_send.assert_called_once()
    assert mock_send.call_args.kwargs["to"] == "parent-hw@test.example"


@patch("app.services.parent_notifications.send_email", return_value=True)
def test_needs_revision_status(mock_send, client):
    _register(client)
    sid = _create_student(client, "Revise")
    _, hw_id = _lesson_with_homework(client, sid)

    portal_token = client.get(f"/students/{sid}/portal-link").json()["portal_token"]
    client.post("/portal/session", json={"portal_token": portal_token})
    client.post(
        f"/portal/homework/{hw_id}/submit",
        files={"file": ("x.png", io.BytesIO(b"\x89PNG\r\n"), "image/png")},
    )

    sub_id = client.get(f"/homework/{hw_id}/submissions").json()[0]["id"]
    rev = client.post(
        f"/homework/{hw_id}/submissions/{sub_id}/review",
        json={"status": "needs_revision", "tutor_comment": "Переделай задачу 3"},
    )
    assert rev.status_code == 200
    assert rev.json()["status"] == "needs_revision"
    mock_send.assert_not_called()
