"""ARQ worker entrypoint: arq app.worker_settings.WorkerSettings"""

from __future__ import annotations

from arq.connections import RedisSettings

from app.config import get_settings
from app.database import init_db
from app.services.job_tasks import build_pdf_task, generate_homework_task


async def startup(ctx) -> None:
    init_db()


async def shutdown(ctx) -> None:
    pass


class WorkerSettings:
    functions = [generate_homework_task, build_pdf_task]
    on_startup = startup
    on_shutdown = shutdown
    max_jobs = 8
    job_timeout = 600
    keep_result = 3600

    @staticmethod
    def redis_settings() -> RedisSettings:
        cfg = get_settings()
        url = cfg.redis_url.strip() or "redis://localhost:6379/0"
        return RedisSettings.from_dsn(url)
