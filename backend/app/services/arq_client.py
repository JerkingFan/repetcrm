"""ARQ Redis pool for background worker dispatch."""

from __future__ import annotations

import logging

from app.config import get_settings

logger = logging.getLogger(__name__)

_pool = None


async def get_arq_pool():
    global _pool
    if _pool is not None:
        return _pool

    url = get_settings().redis_url.strip()
    if not url:
        return None

    try:
        from arq import create_pool
        from arq.connections import RedisSettings

        _pool = await create_pool(RedisSettings.from_dsn(url))
        logger.info("ARQ pool connected")
        return _pool
    except Exception as exc:
        logger.warning("ARQ pool unavailable: %s", exc)
        return None


async def close_arq_pool() -> None:
    global _pool
    if _pool is not None:
        try:
            await _pool.close()
        except Exception:
            pass
    _pool = None


async def enqueue_arq_task(task_name: str, job_id: str, *args) -> bool:
    pool = await get_arq_pool()
    if pool is None:
        return False
    try:
        await pool.enqueue_job(task_name, job_id, *args)
        return True
    except Exception as exc:
        logger.warning("ARQ enqueue failed task=%s job=%s: %s", task_name, job_id, exc)
        return False
