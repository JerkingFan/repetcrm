"""Manual payment receipts: parent uploads proof, tutor confirms."""

import uuid


def _register(client):
    email = f"tutor_{uuid.uuid4().hex}@test.example"
    client.post("/auth/register", json={"email": email, "password": "SecurePass99", "name": "Tutor"})


def _pdf_file():
    content = b"%PDF-1.4\n1 0 obj<<>>endobj\ntrailer<<>>\n%%EOF"
    return ("receipt.pdf", content, "application/pdf")


def test_payment_requisites_and_receipt_flow(client):
    _register(client)
    client.put(
        "/auth/payment-requisites",
        json={"payment_details": "IBAN: BY00TEST\nБанк: Тестбанк"},
    )

    sid = client.post(
        "/students",
        json={
            "name": "Kid",
            "subject": "Math",
            "grade": "7",
            "parent_name": "Mom",
            "parent_email": "mom@test.example",
        },
    ).json()["id"]
    token = client.get(f"/students/{sid}/parent-portal-link").json()["parent_portal_token"]
    client.post("/parent-portal/session", json={"parent_portal_token": token})

    details = client.get("/parent-portal/payment-details")
    assert details.status_code == 200
    assert details.json()["has_requisites"] is True
    assert "BY00TEST" in details.json()["payment_details"]

    fname, data, mime = _pdf_file()
    created = client.post(
        "/parent-portal/payments/receipt",
        data={"amount": "120", "note": "за 3 урока"},
        files={"file": (fname, data, mime)},
    )
    assert created.status_code == 201, created.text
    receipt_id = created.json()["id"]
    assert created.json()["status"] == "pending"

    pending = client.get("/payments/receipts?status=pending")
    assert pending.status_code == 200
    assert any(r["id"] == receipt_id for r in pending.json())

    dash = client.get("/dashboard/extended")
    assert any(r["id"] == receipt_id for r in dash.json()["pending_payment_receipts"])

    confirmed = client.post(f"/payments/receipts/{receipt_id}/confirm")
    assert confirmed.status_code == 200
    assert confirmed.json()["status"] == "confirmed"

    student = client.get(f"/students/{sid}")
    assert student.json()["balance"] == 120.0


def test_receipt_requires_requisites(client):
    _register(client)
    sid = client.post("/students", json={"name": "Kid", "subject": "M", "grade": "5"}).json()["id"]
    token = client.get(f"/students/{sid}/parent-portal-link").json()["parent_portal_token"]
    client.post("/parent-portal/session", json={"parent_portal_token": token})

    fname, data, mime = _pdf_file()
    resp = client.post(
        "/parent-portal/payments/receipt",
        data={"amount": "50"},
        files={"file": (fname, data, mime)},
    )
    assert resp.status_code == 400
