"""ARQ worker entrypoint: arq app.worker_settings.WorkerSettings"""

from __future__ import annotations

from arq.connections import RedisSettings
from arq.cron import cron

from app.config import get_settings
from app.database import init_db
from app.services.job_tasks import build_pdf_task, generate_homework_task
from app.services.reminder_tasks import run_daily_reminders


async def startup(ctx) -> None:
    from app.logging_setup import configure_logging

    configure_logging(get_settings())
    init_db()


async def shutdown(ctx) -> None:
    pass


class WorkerSettings:
    functions = [generate_homework_task, build_pdf_task, run_daily_reminders]
    cron_jobs = [
        cron(
            run_daily_reminders,
            hour={get_settings().reminder_cron_hour},
            minute=0,
            run_at_startup=False,
        )
    ]
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
