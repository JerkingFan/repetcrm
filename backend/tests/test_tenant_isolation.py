"""Multi-tenant isolation — tutor A cannot access tutor B data."""

import uuid


def _register(client, email: str, password: str = "SecurePass99", name: str = "Tutor"):
    return client.post("/auth/register", json={"email": email, "password": password, "name": name})


def _login(client, email: str, password: str = "SecurePass99"):
    client.post("/auth/logout")
    return client.post("/auth/login", json={"email": email, "password": password})


def test_student_isolation_between_tutors(client):
    email_a = f"tutor-a-{uuid.uuid4().hex[:8]}@test.example"
    email_b = f"tutor-b-{uuid.uuid4().hex[:8]}@test.example"

    assert _register(client, email_a, name="A").status_code == 200
    _login(client, email_a)
    student = client.post(
        "/students",
        json={"name": "Student A", "subject": "Math", "grade": "5"},
    ).json()
    assert "id" in student

    assert _register(client, email_b, name="B").status_code == 200
    _login(client, email_b)

    assert client.get(f"/students/{student['id']}").status_code == 404
    assert client.get(f"/students/{student['id']}/lessons").status_code == 404
    assert client.delete(f"/students/{student['id']}").status_code == 404


def test_board_isolation_between_tutors(client):
    email_a = f"board-a-{uuid.uuid4().hex[:8]}@test.example"
    email_b = f"board-b-{uuid.uuid4().hex[:8]}@test.example"

    assert _register(client, email_a).status_code == 200
    _login(client, email_a)
    board = client.post("/boards", json={"title": "Private"}).json()
    assert "id" in board

    assert _register(client, email_b).status_code == 200
    _login(client, email_b)

    assert client.get(f"/boards/{board['id']}").status_code == 404
    assert client.put(f"/boards/{board['id']}", json={"title": "Hack"}).status_code == 404
