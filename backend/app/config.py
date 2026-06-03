from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

_BACKEND_DIR = Path(__file__).resolve().parent.parent
_ENV_FILE = _BACKEND_DIR / ".env"

# Ключи из backend/.env — файл важнее устаревших переменных Windows
_ENV_FILE_KEYS = {
    "SECRET_KEY": "secret_key",
    "DATABASE_URL": "database_url",
    "CORS_ORIGINS": "cors_origins",
    "HOMEWORK_AI_PROVIDER": "homework_ai_provider",
    "OPENROUTER_API_KEY": "openrouter_api_key",
    "OPENROUTER_MODEL": "openrouter_model",
    "OPENROUTER_BASE_URL": "openrouter_base_url",
    "OPENROUTER_TIMEOUT_SEC": "openrouter_timeout_sec",
    "OPENROUTER_MAX_TOKENS": "openrouter_max_tokens",
    "LOCAL_ENABLE_TRANSFORMERS": "local_enable_transformers",
    "AI_USE_OLLAMA": "ai_use_ollama",
    "LATEX_ONLINE_COMPILE": "latex_online_compile",
}


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(_ENV_FILE),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    secret_key: str = "repetcrm-dev-secret-change-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24 * 7
    database_url: str = "sqlite:///./data/repetcrm.db"
    openrouter_api_key: str = ""
    openrouter_model: str = "qwen/qwen-2.5-7b-instruct"
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    openrouter_timeout_sec: float = 120.0
    openrouter_max_tokens: int = 4096
    openrouter_site_url: str = "http://localhost:3000"
    openrouter_app_name: str = "RepetCRM"
    ai_use_ollama: bool = False
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "qwen2.5:3b"
    ollama_timeout_sec: float = 180.0
    local_model_id: str = "Qwen/Qwen2.5-1.5B-Instruct"
    local_model_dir: str = "./models/Qwen2.5-1.5B-Instruct"
    local_model_max_tokens: int = 1200
    local_model_preload: bool = True
    local_enable_transformers: bool = False
    local_transformers_timeout_sec: float = 900.0
    ai_allow_template_fallback: bool = True
    homework_ai_provider: str = "smart"
    latex_online_compile: bool = True
    latex_online_url: str = "https://latexonline.cc/compile"
    media_dir: str = "./media"
    cors_origins: str = (
        "http://localhost:3000,http://127.0.0.1:3000,"
        "http://localhost:3001,http://127.0.0.1:3001"
    )
    cors_allow_localhost_regex: bool = True

    @property
    def ollama_generate_url(self) -> str:
        return f"{self.ollama_base_url.rstrip('/')}/api/generate"

    @property
    def ollama_chat_url(self) -> str:
        return f"{self.ollama_base_url.rstrip('/')}/api/chat"

    @property
    def ollama_tags_url(self) -> str:
        return f"{self.ollama_base_url.rstrip('/')}/api/tags"


def get_settings() -> Settings:
    """Перечитывает backend/.env; файл важнее переменных окружения Windows."""
    base = Settings()
    if not _ENV_FILE.is_file():
        return base
    try:
        from dotenv import dotenv_values
    except ImportError:
        return base

    raw = dotenv_values(_ENV_FILE)
    updates: dict = {}
    for env_key, field in _ENV_FILE_KEYS.items():
        val = raw.get(env_key)
        if val is None or not str(val).strip():
            continue
        v = str(val).strip()
        if field in (
            "local_enable_transformers",
            "ai_use_ollama",
            "latex_online_compile",
        ):
            updates[field] = v.lower() in ("1", "true", "yes", "on")
        elif field in ("openrouter_timeout_sec", "openrouter_max_tokens"):
            updates[field] = float(v) if "." in v else int(v)
        else:
            updates[field] = v
    if updates:
        return base.model_copy(update=updates)
    return base


settings = get_settings()
