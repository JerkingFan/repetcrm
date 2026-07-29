"""backend/.env loading edge cases."""

from pathlib import Path

from app.config import get_settings, openrouter_key_hint


def test_openrouter_key_hint_masks_secret():
    assert openrouter_key_hint("") == "ключ не задан"
    assert openrouter_key_hint("sk-or-v1-abcdef123456") == "ключ …123456"


def test_single_openrouter_key_in_env_file():
    env_path = Path(__file__).resolve().parent.parent / ".env"
    if not env_path.is_file():
        return
    lines = [
        line
        for line in env_path.read_text(encoding="utf-8").splitlines()
        if line.strip().startswith("OPENROUTER_API_KEY=")
    ]
    assert len(lines) == 1, "в backend/.env должен быть ровно один OPENROUTER_API_KEY"
    cfg = get_settings()
    assert cfg.openrouter_api_key.strip()
