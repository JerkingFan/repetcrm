"""Persist background job state in Redis (survives polling across brief outages)."""

from __future__ import annotations

import json
import logging
import time
from typing import Any

from app.config import get_settings
from app.redis_client import get_redis
from app.services.job_types import Job

logger = logging.getLogger(__name__)

_JOB_PREFIX = "job:v1:"
_ACTIVE_PREFIX = "job:active:v1:"


def _job_key(job_id: str) -> str:
    return f"{_JOB_PREFIX}{job_id}"


def _active_key(owner_user_id: int, key_type: str, key_value: int) -> str:
    return f"{_ACTIVE_PREFIX}{owner_user_id}:{key_type}:{key_value}"


def _ttl_for_status(status: str, expires_at_ms: int) -> int:
    cfg = get_settings()
    if status in ("done", "error"):
        return max(60, cfg.job_retention_sec)
    now_ms = int(time.time() * 1000)
    remaining = max(1, (expires_at_ms - now_ms) // 1000) if expires_at_ms else cfg.job_ttl_sec
    return max(remaining, 60)


def job_to_dict(job) -> dict[str, Any]:
    return {
        "id": job.id,
        "type": job.type,
        "status": job.status,
        "created_at_ms": job.created_at_ms,
        "updated_at_ms": job.updated_at_ms,
        "owner_user_id": job.owner_user_id,
        "lesson_id": job.lesson_id,
        "homework_id": job.homework_id,
        "result": job.result,
        "error": job.error,
        "expires_at_ms": job.expires_at_ms,
    }


def job_from_dict(data: dict[str, Any]) -> Job:
    return Job(
        id=data["id"],
        type=data["type"],
        status=data["status"],
        created_at_ms=int(data["created_at_ms"]),
        updated_at_ms=int(data["updated_at_ms"]),
        owner_user_id=int(data["owner_user_id"]),
        lesson_id=data.get("lesson_id"),
        homework_id=data.get("homework_id"),
        result=data.get("result"),
        error=data.get("error"),
        expires_at_ms=int(data.get("expires_at_ms") or 0),
    )


def save_job(job) -> None:
    redis = get_redis()
    if redis is None:
        return
    try:
        payload = json.dumps(job_to_dict(job), ensure_ascii=False)
        redis.setex(_job_key(job.id), _ttl_for_status(job.status, job.expires_at_ms), payload)
    except Exception as exc:
        logger.warning("job_store save failed id=%s: %s", job.id, exc)


def load_job(job_id: str) -> Job | None:
    redis = get_redis()
    if redis is None:
        return None
    try:
        raw = redis.get(_job_key(job_id))
        if not raw:
            return None
        return job_from_dict(json.loads(raw))
    except Exception as exc:
        logger.warning("job_store load failed id=%s: %s", job_id, exc)
        return None


def set_active(owner_user_id: int, key_type: str, key_value: int, job_id: str) -> None:
    redis = get_redis()
    if redis is None:
        return
    try:
        ttl = max(60, get_settings().job_ttl_sec)
        redis.setex(_active_key(owner_user_id, key_type, key_value), ttl, job_id)
    except Exception as exc:
        logger.warning("job_store set_active failed: %s", exc)


def get_active(owner_user_id: int, key_type: str, key_value: int) -> str | None:
    redis = get_redis()
    if redis is None:
        return None
    try:
        return redis.get(_active_key(owner_user_id, key_type, key_value))
    except Exception as exc:
        logger.warning("job_store get_active failed: %s", exc)
        return None


def clear_active(owner_user_id: int, key_type: str, key_value: int) -> None:
    redis = get_redis()
    if redis is None:
        return
    try:
        redis.delete(_active_key(owner_user_id, key_type, key_value))
    except Exception as exc:
        logger.warning("job_store clear_active failed: %s", exc)


def recover_stale_jobs() -> int:
    """
    After API restart, active jobs cannot continue in-process.
    Mark them failed so clients get a clear error instead of 404.
    """
    redis = get_redis()
    if redis is None:
        return 0

    recovered = 0
    try:
        for key in redis.scan_iter(f"{_ACTIVE_PREFIX}*"):
            job_id = redis.get(key)
            if not job_id:
                redis.delete(key)
                continue
            job = load_job(job_id)
            if job and job.status in ("queued", "running"):
                job.status = "error"
                job.error = "Сервер перезапущен. Попробуйте снова."
                job.updated_at_ms = int(time.time() * 1000)
                save_job(job)
                recovered += 1
            redis.delete(key)
    except Exception as exc:
        logger.warning("job_store recover_stale_jobs failed: %s", exc)

    if recovered:
        logger.info("Recovered %s stale background job(s) after restart", recovered)
    return recovered
