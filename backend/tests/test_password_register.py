"""Registration rejects weak passwords."""


def test_register_rejects_weak_password(client):
    email = "weak-pass@test.example"
    response = client.post(
        "/auth/register",
        json={"email": email, "password": "short1", "name": "T"},
    )
    assert response.status_code == 422
