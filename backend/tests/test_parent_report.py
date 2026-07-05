"""Parent monthly report JSON, PDF, and email."""

import uuid
from datetime import date
from unittest.mock import patch

from app.services.parent_report_service import current_month_str


def _register(client):
    email = f"tutor_{uuid.uuid4().hex}@test.example"
    client.post("/auth/register", json={"email": email, "password": "SecurePass99", "name": "Tutor"})


def _student_with_parent(client):
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
    assert created.status_code == 201, created.text
    return created.json()["id"]


def test_tutor_parent_report_json_and_pdf(client):
    _register(client)
    sid = _student_with_parent(client)
    month = current_month_str()
    today = date.today().isoformat()

    client.post(
        "/lessons",
        json={
            "student_id": sid,
            "lesson_date": today,
            "lesson_time": "15:00",
            "duration_minutes": 60,
            "payment_amount": 40,
            "is_paid": True,
        },
    )

    report = client.get(f"/students/{sid}/parent-report?month={month}")
    assert report.status_code == 200, report.text
    body = report.json()
    assert body["student_name"] == "Kid"
    assert body["lessons_total"] >= 1
    assert body["month"] == month

    pdf = client.get(f"/students/{sid}/parent-report.pdf?month={month}")
    assert pdf.status_code == 200
    assert pdf.headers["content-type"].startswith("application/pdf")
    assert pdf.content[:4] == b"%PDF"


def test_parent_portal_report_json_and_pdf(client):
    _register(client)
    sid = _student_with_parent(client)
    month = current_month_str()
    token = client.get(f"/students/{sid}/parent-portal-link").json()["parent_portal_token"]
    client.post("/parent-portal/session", json={"parent_portal_token": token})

    report = client.get(f"/parent-portal/report?month={month}")
    assert report.status_code == 200
    assert report.json()["student_name"] == "Kid"

    pdf = client.get(f"/parent-portal/report.pdf?month={month}")
    assert pdf.status_code == 200
    assert pdf.content[:4] == b"%PDF"


@patch("app.services.mailer.send_email_with_attachment", return_value=True)
def test_send_parent_report_email(mock_send, client):
    _register(client)
    sid = _student_with_parent(client)
    month = current_month_str()

    sent = client.post(f"/students/{sid}/parent-report/send?month={month}")
    assert sent.status_code == 200, sent.text
    assert sent.json()["message"] == "Report sent"
    mock_send.assert_called_once()
    kwargs = mock_send.call_args.kwargs
    assert kwargs["to"] == "anna@parent.test"
    assert month in kwargs["attachment_filename"]
    assert kwargs["attachment_bytes"][:4] == b"%PDF"


def test_send_parent_report_requires_email(client):
    _register(client)
    created = client.post(
        "/students",
        json={"name": "NoParent", "subject": "Math", "grade": "7"},
    )
    sid = created.json()["id"]
    month = current_month_str()
    resp = client.post(f"/students/{sid}/parent-report/send?month={month}")
    assert resp.status_code == 400
    assert "email" in resp.json()["detail"].lower()


def test_parent_report_invalid_month(client):
    _register(client)
    sid = _student_with_parent(client)
    resp = client.get(f"/students/{sid}/parent-report?month=not-a-month")
    assert resp.status_code == 400
