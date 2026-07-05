import uuid

import pytest
from fastapi.testclient import TestClient


@pytest.fixture()
def client(tmp_path, monkeypatch):
    db_path = tmp_path / f"test_{uuid.uuid4().hex}.db"
    media_path = tmp_path / "media"
    media_path.mkdir(parents=True, exist_ok=True)

    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path.as_posix()}")
    monkeypatch.setenv("MEDIA_DIR", str(media_path))
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.setenv("API_RATE_LIMIT_ENABLED", "false")
    monkeypatch.setenv("AUTH_REGISTER_MAX_PER_IP", "1000")
    monkeypatch.setenv("AUTH_LOGIN_MAX_FAILURES", "1000")
    monkeypatch.setenv("PAYMENT_WEBHOOK_SECRET", "")

    import importlib
    import app.config as config_module
    import app.database as database_module
    import app.middleware.api_rate_limit as rate_limit_module
    import app.main as main_module

    monkeypatch.setattr(config_module, "_ENV_FILE", tmp_path / "missing.env")
    rate_limit_module._limiter = None
    importlib.reload(config_module)
    importlib.reload(database_module)
    importlib.reload(main_module)

    _orig_get_settings = config_module.get_settings

    def _test_get_settings():
        return _orig_get_settings().model_copy(update={"payment_webhook_secret": ""})

    monkeypatch.setattr(config_module, "get_settings", _test_get_settings)
    import app.services.payment_service as payment_service_module

    monkeypatch.setattr(payment_service_module, "get_settings", _test_get_settings)

    app = main_module.app

    database_module.init_db()

    db_seed = database_module.SessionLocal()
    try:
        from app.services.prompt_marketplace_seed import ensure_prompt_catalog_seeded

        ensure_prompt_catalog_seeded(db_seed)
    finally:
        db_seed.close()

    def override_get_db():
        db = database_module.SessionLocal()
        try:
            yield db
        finally:
            db.close()

    from app.database import get_db

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as c:
        yield c

    app.dependency_overrides.clear()
