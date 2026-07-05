"""Board share_writable — guest read-only by default."""

import uuid


def _register(client, email: str, password: str = "SecurePass99"):
    return client.post("/auth/register", json={"email": email, "password": password, "name": "T"})


def _login(client, email: str, password: str = "SecurePass99"):
    client.post("/auth/logout")
    return client.post("/auth/login", json={"email": email, "password": password})


def test_new_board_guest_write_disabled_by_default(client):
    email = f"owner-board-{uuid.uuid4().hex[:8]}@test.example"
    assert _register(client, email).status_code == 200
    _login(client, email)

    created = client.post("/boards", json={"title": "Test"}).json()
    assert created["share_writable"] is False

    board_id = created["id"]
    token = created["share_token"]

    put = client.put(
        f"/boards/{board_id}/public?token={token}",
        json={"state_json": {"version": 1, "strokes": [], "texts": [], "images": []}},
    )
    assert put.status_code == 403

    _login(client, email)
    client.put(f"/boards/{board_id}", json={"share_writable": True})
    put2 = client.put(
        f"/boards/{board_id}/public?token={token}",
        json={"state_json": {"version": 1, "strokes": [], "texts": [], "images": []}},
    )
    assert put2.status_code == 200


def test_owner_can_toggle_share_writable(client):
    email = f"owner-toggle-{uuid.uuid4().hex[:8]}@test.example"
    assert _register(client, email).status_code == 200
    _login(client, email)

    board = client.post("/boards").json()
    updated = client.put(f"/boards/{board['id']}", json={"share_writable": True}).json()
    assert updated["share_writable"] is True
