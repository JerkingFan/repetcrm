from __future__ import annotations

import asyncio
import secrets
import time
from dataclasses import dataclass
from typing import Any, Literal


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


class InMemoryJobQueue:
    """
    MVP job queue:
    - in-memory (single process)
    - one active job per (user, lesson)
    - jobs can be polled by id
    """

    def __init__(self) -> None:
        self._lock = asyncio.Lock()
        self._jobs: dict[str, Job] = {}
        self._active_by_key: dict[tuple[int, str], str] = {}
        self._semaphores: dict[int, asyncio.Semaphore] = {}

    def _now_ms(self) -> int:
        return int(time.time() * 1000)

    def _new_id(self) -> str:
        # short, URL-safe, unique enough for MVP
        return secrets.token_urlsafe(16)

    async def get(self, job_id: str) -> Job | None:
        async with self._lock:
            return self._jobs.get(job_id)

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
            existing_id = self._active_by_key.get(key)
            if existing_id:
                existing = self._jobs.get(existing_id)
                if existing and existing.status in ("queued", "running"):
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
            )
            self._jobs[job_id] = job
            self._active_by_key[key] = job_id

        async def _runner():
            sem = self._semaphores.setdefault(owner_user_id, asyncio.Semaphore(1))
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
                    async with self._lock:
                        active = self._active_by_key.get(key)
                        if active == job.id:
                            self._active_by_key.pop(key, None)

        asyncio.create_task(_runner())
        return job


job_queue = InMemoryJobQueue()

