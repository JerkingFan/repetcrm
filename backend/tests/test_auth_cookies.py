"""Cookie-based access token auth."""

import uuid


def test_login_sets_access_cookie(client):
    email = f"cookie-{uuid.uuid4().hex[:8]}@test.example"
    reg = client.post(
        "/auth/register",
        json={"email": email, "password": "SecurePass99", "name": "T"},
    )
    assert reg.status_code == 200
    assert "repetcrm_access" in reg.cookies
    assert reg.json()["token_type"] == "cookie"

    me = client.get("/auth/me")
    assert me.status_code == 200
    assert me.json()["email"] == email


def test_logout_clears_access_cookie(client):
    email = f"logout-{uuid.uuid4().hex[:8]}@test.example"
    reg = client.post(
        "/auth/register",
        json={"email": email, "password": "SecurePass99", "name": "T"},
    )
    assert reg.status_code == 200

    out = client.post("/auth/logout")
    assert out.status_code == 204

    me = client.get("/auth/me")
    assert me.status_code == 401
