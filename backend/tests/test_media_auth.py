import os
import secrets
import uuid

from fastapi.testclient import TestClient


def _register(client, password: str = "SecurePass99"):
    email = f"tutor-{uuid.uuid4().hex[:8]}@test.example"
    return client.post(
        "/auth/register",
        json={"email": email, "password": password, "name": "Tutor"},
    )


def test_media_board_requires_auth(client):
    reg = _register(client)
    assert reg.status_code == 200

    board_resp = client.post("/boards", json={"title": "Test"})
    assert board_resp.status_code == 200
    board = board_resp.json()
    board_id = board["id"]
    share = board["share_token"]

    media_root = os.environ["MEDIA_DIR"]
    board_dir = os.path.join(media_root, "boards", str(board_id))
    os.makedirs(board_dir, exist_ok=True)
    fname = f"{secrets.token_hex(12)}.png"
    with open(os.path.join(board_dir, fname), "wb") as f:
        f.write(b"\x89PNG\r\n")

    url = f"/media/boards/{board_id}/{fname}"
    anon = TestClient(client.app)
    assert anon.get(url).status_code == 401
    assert anon.get(url, params={"token": "wrong-token"}).status_code == 401
    assert anon.get(url, params={"token": share}).status_code == 200
    assert client.get(url).status_code == 200


def test_docs_hidden_in_production(tmp_path, monkeypatch):
    db_path = tmp_path / "prod_docs.db"
    media_path = tmp_path / "media"
    media_path.mkdir(parents=True, exist_ok=True)

    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("SECRET_KEY", "x" * 48)
    monkeypatch.setenv("PAYMENT_WEBHOOK_SECRET", "y" * 48)
    monkeypatch.setenv("COOKIE_SECURE", "true")
    monkeypatch.setenv("CORS_ALLOW_LOCALHOST_REGEX", "false")
    monkeypatch.setenv("CORS_ORIGINS", "https://repetcrm.ru")
    monkeypatch.setenv("FRONTEND_PUBLIC_URL", "https://repetcrm.ru")
    monkeypatch.setenv("REDIS_URL", "redis://:testsecret@127.0.0.1:6379/0")
    monkeypatch.setenv("METRICS_TOKEN", "z" * 48)
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path.as_posix()}")
    monkeypatch.setenv("MEDIA_DIR", str(media_path))

    import app.config as config_module

    monkeypatch.setattr(config_module, "_ENV_FILE", tmp_path / "missing.env")

    import importlib
    import app.database as database_module
    import app.db_migrate as db_migrate_module
    import app.main as main_module
    import app.redis_client as redis_module
    import app.startup_checks as startup_checks_module

    importlib.reload(config_module)
    importlib.reload(database_module)
    importlib.reload(db_migrate_module)
    database_module.init_db()

    class _FakeRedis:
        pass

    monkeypatch.setattr(startup_checks_module, "validate_production_redis_connected", lambda _cfg: None)
    monkeypatch.setattr(redis_module, "get_redis", lambda: _FakeRedis())

    importlib.reload(main_module)

    with TestClient(main_module.app) as c:
        assert c.get("/docs").status_code == 404
        health = c.get("/health")
        assert health.status_code == 200, health.text
