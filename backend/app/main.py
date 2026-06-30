import asyncio
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.config import get_settings
from app.database import init_db
from app.redis_client import close_redis
from app.routers import auth_router, students, lessons, homework, ai
from app.routers import boards
from app.services.homework_ai import get_ai_status
from app.services.openrouter_client import is_configured as openrouter_configured
from app.services.local_llm import local_model_available, preload_model_background


@asynccontextmanager
async def lifespan(app: FastAPI):
    os.makedirs("data", exist_ok=True)
    cfg = get_settings()
    os.makedirs(cfg.media_dir, exist_ok=True)
    init_db()
    print("[AI] API ready; provider check runs in background")

    async def _log_ai_status() -> None:
        try:
            status = await asyncio.wait_for(get_ai_status(), timeout=15.0)
        except Exception as e:
            print(f"[AI] status check skipped: {e}")
            return
        if openrouter_configured():
            or_status = status.get("openrouter", {})
            print(f"[AI] provider={cfg.homework_ai_provider} model={cfg.openrouter_model}")
            print(f"[AI] {status['local_llm'].get('eta_hint', '')}")
            if not or_status.get("online"):
                print("[AI] OpenRouter недоступен — проверьте ключ и сеть")
        else:
            llm = status["local_llm"]
            if llm.get("available") and cfg.local_enable_transformers:
                print(f"[AI] Hugging Face: {llm.get('model_file')} ({llm.get('device')})")
                if cfg.local_model_preload and local_model_available():
                    preload_model_background()
            else:
                print("[AI] Задайте OPENROUTER_API_KEY (продакшен без локальной модели)")

    asyncio.create_task(_log_ai_status())
    yield
    close_redis()


app = FastAPI(title="RepetCRM API", version="1.0.0", lifespan=lifespan)

_cfg = get_settings()
os.makedirs(_cfg.media_dir, exist_ok=True)
app.mount("/media", StaticFiles(directory=_cfg.media_dir), name="media")
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

app.include_router(auth_router.router)
app.include_router(students.router)
app.include_router(lessons.router)
app.include_router(homework.router)
app.include_router(ai.router)
app.include_router(boards.router)


@app.get("/health")
def health():
    return {"status": "ok"}
