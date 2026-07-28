import asyncio
import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.database import init_db
from app.logging_setup import configure_logging
from app.metrics import setup_metrics
from app.sentry_setup import init_sentry
from app.middleware.api_rate_limit import ApiRateLimitMiddleware
from app.redis_client import close_redis, get_redis
from app.routers import auth_router, students, lessons, homework, ai
from app.routers import boards, media, data_transfer, portal, calendar_router, homework_templates
from app.routers import payments, analytics, prompt_marketplace, parent_portal, booking, payment_receipts
from app.routers import reschedule
from app.services.homework_ai import get_ai_status
from app.services.db_startup import get_db_health, run_startup_db_checks
from app.services.db_safeguard import run_pre_db_startup, validate_production_user_floor
from app.services.job_store import recover_stale_jobs
from app.services.arq_client import close_arq_pool
from app.services.openrouter_client import is_configured as openrouter_configured
from app.services.local_llm import local_model_available, preload_model_background
from app.startup_checks import validate_production_settings

logger = logging.getLogger("app.main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    os.makedirs("data", exist_ok=True)
    cfg = get_settings()
    os.makedirs(cfg.media_dir, exist_ok=True)
    pre_backup = run_pre_db_startup(cfg)
    init_db()
    from app.database import SessionLocal
    from app.services.prompt_marketplace_seed import ensure_prompt_catalog_seeded

    with SessionLocal() as db:
        seeded = ensure_prompt_catalog_seeded(db)
        if seeded:
            logger.info("prompt marketplace seeded", extra={"count": seeded})
    db_report = run_startup_db_checks(skip_backup=pre_backup is not None)
    validate_production_user_floor(cfg, db_report.users_count)
    logger.info(
        "database ready",
        extra={
            "backend": db_report.backend,
            "users_count": db_report.users_count,
            "backup_path": db_report.backup_path,
        },
    )
    for warning in db_report.warnings:
        logger.warning(warning)
    get_redis()
    from app.routers.boards import setup_board_bus, shutdown_board_bus

    await setup_board_bus()
    recovered = recover_stale_jobs()
    if recovered:
        logger.info("recovered stale jobs", extra={"count": recovered})
    logger.info("API ready; AI provider check runs in background")

    async def _log_ai_status() -> None:
        try:
            status = await asyncio.wait_for(get_ai_status(), timeout=15.0)
        except Exception as e:
            logger.warning("AI status check skipped: %s", e)
            return
        if openrouter_configured():
            or_status = status.get("openrouter", {})
            logger.info(
                "AI provider configured",
                extra={
                    "provider": cfg.homework_ai_provider,
                    "model": cfg.openrouter_model,
                    "openrouter_online": or_status.get("online"),
                },
            )
            if not or_status.get("online"):
                logger.warning("OpenRouter unavailable — check API key and network")
        else:
            llm = status["local_llm"]
            if llm.get("available") and cfg.local_enable_transformers:
                logger.info(
                    "local Hugging Face model",
                    extra={"model_file": llm.get("model_file"), "device": llm.get("device")},
                )
                if cfg.local_model_preload and local_model_available():
                    preload_model_background()
            else:
                logger.warning("OPENROUTER_API_KEY not set (production should use OpenRouter)")

    asyncio.create_task(_log_ai_status())
    yield
    from app.routers.boards import shutdown_board_bus

    await shutdown_board_bus()
    await close_arq_pool()
    close_redis()


_cfg = get_settings()
configure_logging(_cfg)
init_sentry(_cfg)
validate_production_settings(_cfg)

_docs_url = None if _cfg.is_production else "/docs"
_redoc_url = None if _cfg.is_production else "/redoc"
_openapi_url = None if _cfg.is_production else "/openapi.json"

app = FastAPI(
    title="RepetCRM API",
    version="1.0.0",
    lifespan=lifespan,
    docs_url=_docs_url,
    redoc_url=_redoc_url,
    openapi_url=_openapi_url,
)

os.makedirs(_cfg.media_dir, exist_ok=True)
origins = [o.strip() for o in _cfg.cors_origins.split(",") if o.strip()]
cors_kwargs: dict = {
    "allow_origins": origins,
    "allow_credentials": True,
    "allow_methods": ["*"],
    "allow_headers": ["*"],
}
if _cfg.cors_allow_localhost_regex:
    cors_kwargs["allow_origin_regex"] = r"http://(localhost|127\.0\.0\.1)(:\d+)?"

app.add_middleware(CORSMiddleware, **cors_kwargs)
app.add_middleware(ApiRateLimitMiddleware)
setup_metrics(app, _cfg)

app.include_router(auth_router.router)
app.include_router(students.router)
app.include_router(lessons.router)
app.include_router(homework.router)
app.include_router(ai.router)
app.include_router(boards.router)
app.include_router(media.router)
app.include_router(data_transfer.router)
app.include_router(portal.router)
app.include_router(calendar_router.router)
app.include_router(homework_templates.router)
app.include_router(payments.router)
app.include_router(analytics.router)
app.include_router(prompt_marketplace.router)
app.include_router(parent_portal.router)
app.include_router(booking.router)
app.include_router(payment_receipts.router)
app.include_router(reschedule.router)


@app.get("/health")
def health():
    from fastapi.responses import JSONResponse

    from app.services.board_bus import board_bus

    redis = get_redis()
    db_health = get_db_health()
    db_ok = bool(db_health.get("ok"))
    body = {
        "status": "ok" if db_ok else "degraded",
        "redis": "connected" if redis is not None else "disabled",
        "worker": "arq" if redis is not None else "in-process",
        "board_bus": "redis" if board_bus.enabled else "local",
        "database": db_health,
    }
    if not db_ok:
        return JSONResponse(status_code=503, content=body)
    return body
