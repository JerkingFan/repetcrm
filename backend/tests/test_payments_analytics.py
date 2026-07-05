"""Online payments and analytics."""

import json
import uuid
from datetime import date


def _register(client):
    email = f"pay_{uuid.uuid4().hex}@test.example"
    client.post("/auth/register", json={"email": email, "password": "SecurePass99", "name": "Pay Tutor"})


def test_payment_intent_and_webhook(client):
    _register(client)
    st = client.post("/students", json={"name": "Payer", "subject": "Math", "grade": "8"})
    sid = st.json()["id"]

    intent = client.post(
        "/payments/intents",
        json={"student_id": sid, "amount": 80, "provider": "erip"},
    )
    assert intent.status_code == 201
    data = intent.json()
    assert data["status"] == "pending"
    assert data["erip_code"]
    assert data["payment_url"]

    body = json.dumps(
        {"intent_id": data["id"], "external_id": "erip-tx-001", "status": "paid"}
    ).encode()
    wh = client.post(
        "/webhooks/payments",
        content=body,
        headers={"Content-Type": "application/json"},
    )
    assert wh.status_code == 200, wh.text

    student = client.get(f"/students/{sid}")
    assert student.json()["balance"] == 80

    intent2 = client.get(f"/payments/intents/{data['id']}")
    assert intent2.json()["status"] == "paid"


def test_analytics_overview(client):
    _register(client)
    st = client.post("/students", json={"name": "Ana", "subject": "Math", "grade": "7"})
    sid = st.json()["id"]
    lesson = client.post(
        "/lessons",
        json={
            "student_id": sid,
            "lesson_date": date.today().isoformat(),
            "lesson_time": "10:00",
            "payment_amount": 50,
            "is_paid": True,
        },
    )
    assert lesson.status_code == 201
    lid = lesson.json()["lesson"]["id"]
    client.post(
        f"/lessons/{lid}/lesson-report",
        json={
            "is_conducted": True,
            "items": [{"topic": "Test", "work_type": "practice", "difficulty": "medium", "understanding": 3}],
            "prefs": {},
        },
    )

    r = client.get("/analytics/overview")
    assert r.status_code == 200
    body = r.json()
    assert "revenue_by_month" in body
    assert "trial_conversion" in body
    assert "churn" in body


def test_prompt_marketplace_install(client):
    _register(client)
    listed = client.get("/prompt-templates")
    assert listed.status_code == 200
    templates = listed.json()
    assert len(templates) >= 1

    tpl_id = templates[0]["id"]
    install = client.post(f"/prompt-templates/{tpl_id}/install")
    assert install.status_code == 200
    assert install.json()["homework_template_id"]

    my = client.get("/homework-templates")
    assert any(t["name"] == templates[0]["title"] for t in my.json())


def test_verify_webhook_signature_hmac(monkeypatch):
    from app.config import Settings
    from app.services import payment_service

    secret = "test-webhook-secret-32chars-minimum-x"
    cfg = Settings(payment_webhook_secret=secret, app_env="development")
    monkeypatch.setattr(payment_service, "get_settings", lambda: cfg)

    body = b'{"intent_id":1,"status":"paid"}'
    assert payment_service.verify_webhook_signature(body, "invalid") is False
    import hashlib
    import hmac

    good = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    assert payment_service.verify_webhook_signature(body, good) is True
