from __future__ import annotations

import asyncio
import secrets
import time
from dataclasses import dataclass
from typing import Any, Literal

from app.config import get_settings


JobStatus = Literal["queued", "running", "done", "error"]


@dataclass
class Job:
    id: str
    type: str
    status: JobStatus
    created_at_ms: int
    updated_at_ms: int
    owner_user_id: int
    lesson_id: int | None = None
    homework_id: int | None = None
    result: dict[str, Any] | None = None
    error: str | None = None
    expires_at_ms: int = 0


class InMemoryJobQueue:
    """
    MVP job queue (single process):
    - TTL for active jobs (no infinite spinners)
    - retention cleanup for finished jobs
    - global AI concurrency cap
  """

    def __init__(self) -> None:
        self._lock = asyncio.Lock()
        self._jobs: dict[str, Job] = {}
        self._active_by_key: dict[tuple[int, str], str] = {}
        self._semaphores: dict[int, asyncio.Semaphore] = {}
        self._ai_sem: asyncio.Semaphore | None = None

    def _now_ms(self) -> int:
        return int(time.time() * 1000)

    def _ttl_ms(self) -> int:
        return get_settings().job_ttl_sec * 1000

    def _retention_ms(self) -> int:
        return get_settings().job_retention_sec * 1000

    def _ai_semaphore(self) -> asyncio.Semaphore:
        if self._ai_sem is None:
            n = max(1, get_settings().ai_global_concurrency)
            self._ai_sem = asyncio.Semaphore(n)
        return self._ai_sem

    def _new_id(self) -> str:
        return secrets.token_urlsafe(16)

    def _expire_if_needed(self, job: Job) -> None:
        if job.status not in ("queued", "running"):
            return
        if job.expires_at_ms and self._now_ms() > job.expires_at_ms:
            job.status = "error"
            job.error = "Превышено время ожидания. Попробуйте снова."
            job.updated_at_ms = self._now_ms()

    def _prune_finished(self) -> None:
        cutoff = self._now_ms() - self._retention_ms()
        stale_ids = [
            jid
            for jid, job in self._jobs.items()
            if job.status in ("done", "error") and job.updated_at_ms < cutoff
        ]
        for jid in stale_ids:
            self._jobs.pop(jid, None)

    def _clear_active_for_job(self, job: Job) -> None:
        for key, jid in list(self._active_by_key.items()):
            if jid == job.id:
                self._active_by_key.pop(key, None)

    async def get(self, job_id: str) -> Job | None:
        async with self._lock:
            self._prune_finished()
            job = self._jobs.get(job_id)
            if not job:
                return None
            self._expire_if_needed(job)
            if job.status == "error" and job.error and "время ожидания" in job.error:
                self._clear_active_for_job(job)
            return job

    async def _set(self, job: Job) -> None:
        async with self._lock:
            self._jobs[job.id] = job

    async def enqueue_unique(
        self,
        *,
        owner_user_id: int,
        key_type: str,
        key_value: int,
        job_type: str,
        coro_factory,
    ) -> Job:
        """
        If a job with the same (owner, key_type) is active, returns it.
        Otherwise creates a new job and schedules its coroutine.
        """
        key = (owner_user_id, f"{key_type}:{key_value}")
        async with self._lock:
            self._prune_finished()
            existing_id = self._active_by_key.get(key)
            if existing_id:
                existing = self._jobs.get(existing_id)
                if existing and existing.status in ("queued", "running"):
                    self._expire_if_needed(existing)
                    if existing.status in ("queued", "running"):
                        return existing

            job_id = self._new_id()
            now = self._now_ms()
            job = Job(
                id=job_id,
                type=job_type,
                status="queued",
                created_at_ms=now,
                updated_at_ms=now,
                owner_user_id=owner_user_id,
                lesson_id=key_value if key_type == "lesson" else None,
                homework_id=key_value if key_type == "homework" else None,
                expires_at_ms=now + self._ttl_ms(),
            )
            self._jobs[job_id] = job
            self._active_by_key[key] = job_id

        async def _runner():
            sem = self._semaphores.setdefault(owner_user_id, asyncio.Semaphore(1))
            ai_sem = self._ai_semaphore() if job_type == "generate_homework" else None
            try:
                if ai_sem is not None:
                    await ai_sem.acquire()
                async with sem:
                    job.status = "running"
                    job.updated_at_ms = self._now_ms()
                    await self._set(job)
                    try:
                        result = await coro_factory()
                        job.status = "done"
                        job.result = result
                        job.updated_at_ms = self._now_ms()
                        await self._set(job)
                    except Exception as e:
                        job.status = "error"
                        job.error = str(e)
                        job.updated_at_ms = self._now_ms()
                        await self._set(job)
            finally:
                if ai_sem is not None:
                    ai_sem.release()
                async with self._lock:
                    active = self._active_by_key.get(key)
                    if active == job.id:
                        self._active_by_key.pop(key, None)

        asyncio.create_task(_runner())
        return job


job_queue = InMemoryJobQueue()
