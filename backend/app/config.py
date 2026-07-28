from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

_BACKEND_DIR = Path(__file__).resolve().parent.parent
_ENV_FILE = _BACKEND_DIR / ".env"

# Ключи из backend/.env — файл важнее устаревших переменных Windows
_ENV_FILE_KEYS = {
    "SECRET_KEY": "secret_key",
    "DATABASE_URL": "database_url",
    "CORS_ORIGINS": "cors_origins",
    "CORS_ALLOW_LOCALHOST_REGEX": "cors_allow_localhost_regex",
    "HOMEWORK_AI_PROVIDER": "homework_ai_provider",
    "OPENROUTER_API_KEY": "openrouter_api_key",
    "OPENROUTER_MODEL": "openrouter_model",
    "OPENROUTER_BASE_URL": "openrouter_base_url",
    "OPENROUTER_TIMEOUT_SEC": "openrouter_timeout_sec",
    "OPENROUTER_MAX_TOKENS": "openrouter_max_tokens",
    "LOCAL_ENABLE_TRANSFORMERS": "local_enable_transformers",
    "AI_USE_OLLAMA": "ai_use_ollama",
    "LATEX_ONLINE_COMPILE": "latex_online_compile",
    "AUTH_LOGIN_MAX_FAILURES": "auth_login_max_failures",
    "AUTH_LOGIN_WINDOW_SEC": "auth_login_window_sec",
    "AUTH_LOGIN_FAIL_DELAY_SEC": "auth_login_fail_delay_sec",
    "AUTH_REGISTER_MAX_PER_IP": "auth_register_max_per_ip",
    "AUTH_REGISTER_WINDOW_SEC": "auth_register_window_sec",
    "REDIS_URL": "redis_url",
    "DB_POOL_SIZE": "db_pool_size",
    "DB_MAX_OVERFLOW": "db_max_overflow",
    "DB_POOL_TIMEOUT": "db_pool_timeout",
    "DB_POOL_RECYCLE": "db_pool_recycle",
    "REFRESH_TOKEN_EXPIRE_DAYS": "refresh_token_expire_days",
    "COOKIE_SECURE": "cookie_secure",
    "DASHBOARD_CACHE_TTL_SEC": "dashboard_cache_ttl_sec",
    "ACCESS_TOKEN_EXPIRE_MINUTES": "access_token_expire_minutes",
    "BOARD_ASSET_MAX_BYTES": "board_asset_max_bytes",
    "BOARD_PERSIST_DEBOUNCE_SEC": "board_persist_debounce_sec",
    "JOB_TTL_SEC": "job_ttl_sec",
    "JOB_RETENTION_SEC": "job_retention_sec",
    "AI_GLOBAL_CONCURRENCY": "ai_global_concurrency",
    "OPENROUTER_MAX_RETRIES": "openrouter_max_retries",
    "SQLITE_BACKUP_ON_STARTUP": "sqlite_backup_on_startup",
    "SQLITE_BACKUP_DIR": "sqlite_backup_dir",
    "SQLITE_BACKUP_KEEP": "sqlite_backup_keep",
    "SQLITE_MIGRATION_COMPLETED": "sqlite_migration_completed",
    "PRODUCTION_MIN_USERS": "production_min_users",
    "LOG_FORMAT": "log_format",
    "METRICS_ENABLED": "metrics_enabled",
    "METRICS_TOKEN": "metrics_token",
    "API_RATE_LIMIT_ENABLED": "api_rate_limit_enabled",
    "API_RATE_LIMIT_MAX": "api_rate_limit_max",
    "API_RATE_LIMIT_WINDOW_SEC": "api_rate_limit_window_sec",
    "LATEX_CIRCUIT_FAILURES": "latex_circuit_failures",
    "LATEX_CIRCUIT_RESET_SEC": "latex_circuit_reset_sec",
    "OPENROUTER_CIRCUIT_FAILURES": "openrouter_circuit_failures",
    "OPENROUTER_CIRCUIT_RESET_SEC": "openrouter_circuit_reset_sec",
    "SENTRY_DSN": "sentry_dsn",
    "SENTRY_RELEASE": "sentry_release",
    "SENTRY_TRACES_SAMPLE_RATE": "sentry_traces_sample_rate",
    "BOARD_SNAPSHOT_KEEP": "board_snapshot_keep",
    "FRONTEND_PUBLIC_URL": "frontend_public_url",
    "SMTP_HOST": "smtp_host",
    "SMTP_PORT": "smtp_port",
    "SMTP_USER": "smtp_user",
    "SMTP_PASSWORD": "smtp_password",
    "SMTP_FROM": "smtp_from",
    "SMTP_USE_TLS": "smtp_use_tls",
    "TELEGRAM_BOT_TOKEN": "telegram_bot_token",
    "PASSWORD_RESET_EXPIRE_HOURS": "password_reset_expire_hours",
    "PORTAL_SESSION_EXPIRE_DAYS": "portal_session_expire_days",
    "HOMEWORK_SUBMISSION_MAX_BYTES": "homework_submission_max_bytes",
    "REMINDER_CRON_HOUR": "reminder_cron_hour",
    "PAYMENT_WEBHOOK_SECRET": "payment_webhook_secret",
    "MEDIA_DIR": "media_dir",
    "OPENROUTER_SITE_URL": "openrouter_site_url",
    "OPENROUTER_APP_NAME": "openrouter_app_name",
    "OPENROUTER_VISION_MODEL": "openrouter_vision_model",
    "HOMEWORK_AI_REVIEW_ENABLED": "homework_ai_review_enabled",
    "LATEX_ONLINE_URL": "latex_online_url",
    "AI_ALLOW_TEMPLATE_FALLBACK": "ai_allow_template_fallback",
    "REDIS_PASSWORD": "redis_password",
    "APP_ENV": "app_env",
}


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(_ENV_FILE),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_env: str = "development"
    secret_key: str = "repetcrm-dev-secret-change-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 7
    refresh_cookie_name: str = "repetcrm_refresh"
    access_cookie_name: str = "repetcrm_access"
    cookie_secure: bool = False
    database_url: str = "sqlite:///./data/repetcrm.db"
    redis_url: str = ""
    db_pool_size: int = 10
    db_max_overflow: int = 20
    db_pool_timeout: int = 30
    db_pool_recycle: int = 1800
    dashboard_cache_ttl_sec: int = 30
    openrouter_api_key: str = ""
    openrouter_model: str = "qwen/qwen-2.5-7b-instruct"
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    openrouter_timeout_sec: float = 120.0
    openrouter_max_tokens: int = 4096
    openrouter_site_url: str = "http://localhost:3000"
    openrouter_app_name: str = "RepetCRM"
    openrouter_vision_model: str = "google/gemini-2.0-flash-001"
    homework_ai_review_enabled: bool = True
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
    # Auth brute-force protection (in-memory; does not invalidate existing JWT)
    auth_login_max_failures: int = 8
    auth_login_window_sec: int = 60
    auth_login_fail_delay_sec: float = 0.5
    auth_register_max_per_ip: int = 5
    auth_register_window_sec: int = 3600
    board_asset_max_bytes: int = 10 * 1024 * 1024  # 10MB
    board_persist_debounce_sec: float = 6.0
    job_ttl_sec: int = 600
    job_retention_sec: int = 3600
    ai_global_concurrency: int = 8
    openrouter_max_retries: int = 3
    sqlite_backup_on_startup: bool = False
    sqlite_backup_dir: str = "./data/backups"
    sqlite_backup_keep: int = 14
    sqlite_migration_completed: bool = False
    production_min_users: int = 0
    log_format: str = "auto"  # auto | json | text
    metrics_enabled: bool = True
    metrics_token: str = ""
    api_rate_limit_enabled: bool = True
    api_rate_limit_max: int = 120
    api_rate_limit_window_sec: int = 60
    latex_circuit_failures: int = 3
    latex_circuit_reset_sec: int = 60
    openrouter_circuit_failures: int = 3
    openrouter_circuit_reset_sec: int = 60
    sentry_dsn: str = ""
    sentry_release: str = ""
    sentry_traces_sample_rate: float = 0.1
    board_snapshot_keep: int = 20
    frontend_public_url: str = "http://localhost:3000"
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from: str = ""
    smtp_use_tls: bool = True
    telegram_bot_token: str = ""
    password_reset_expire_hours: int = 1
    portal_session_expire_days: int = 30
    homework_submission_max_bytes: int = 15 * 1024 * 1024
    reminder_cron_hour: int = 18  # UTC hour for daily reminders
    payment_webhook_secret: str = ""
    redis_password: str = ""

    @property
    def is_production(self) -> bool:
        return self.app_env.strip().lower() == "production"

    @property
    def public_site_url(self) -> str:
        """Public frontend URL for portal/parent/booking links (not localhost on prod)."""
        url = (self.frontend_public_url or "").strip().rstrip("/")
        lower = url.lower()
        is_local = "localhost" in lower or "127.0.0.1" in lower
        if url and not is_local:
            return url
        if self.is_production:
            for part in self.cors_origins.split(","):
                origin = part.strip().rstrip("/")
                if not origin:
                    continue
                ol = origin.lower()
                if "localhost" in ol or "127.0.0.1" in ol or "example.com" in ol:
                    continue
                return origin
        return url or "http://localhost:3000"

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
            "cookie_secure",
            "sqlite_migration_completed",
            "metrics_enabled",
            "cors_allow_localhost_regex",
            "api_rate_limit_enabled",
            "smtp_use_tls",
        ):
            updates[field] = v.lower() in ("1", "true", "yes", "on")
        elif field in (
            "openrouter_timeout_sec",
            "openrouter_max_tokens",
            "auth_login_max_failures",
            "auth_login_window_sec",
            "auth_register_max_per_ip",
            "auth_register_window_sec",
            "board_asset_max_bytes",
            "access_token_expire_minutes",
            "refresh_token_expire_days",
            "db_pool_size",
            "db_max_overflow",
            "db_pool_timeout",
            "db_pool_recycle",
            "dashboard_cache_ttl_sec",
            "job_ttl_sec",
            "job_retention_sec",
            "ai_global_concurrency",
            "openrouter_max_retries",
            "sqlite_backup_keep",
            "production_min_users",
            "api_rate_limit_max",
            "api_rate_limit_window_sec",
            "latex_circuit_failures",
            "latex_circuit_reset_sec",
            "openrouter_circuit_failures",
            "openrouter_circuit_reset_sec",
            "board_snapshot_keep",
            "sentry_traces_sample_rate",
            "smtp_port",
            "password_reset_expire_hours",
            "portal_session_expire_days",
            "homework_submission_max_bytes",
            "reminder_cron_hour",
        ):
            updates[field] = float(v) if "." in v else int(v)
        elif field in ("auth_login_fail_delay_sec", "board_persist_debounce_sec"):
            updates[field] = float(v)
        elif field == "sqlite_backup_on_startup":
            updates[field] = v.lower() in ("1", "true", "yes", "on")
        elif field == "app_env":
            updates[field] = v.strip().lower()
        else:
            updates[field] = v
    if updates:
        return base.model_copy(update=updates)
    return base


settings = get_settings()
