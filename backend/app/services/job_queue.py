from __future__ import annotations

import asyncio
import logging
import secrets
import time

from app.config import get_settings
from app.services import job_store
from app.services.arq_client import enqueue_arq_task, is_arq_worker_online
from app.services.job_types import Job

logger = logging.getLogger(__name__)

# ARQ registers tasks by function name
ARQ_TASK_GENERATE_HOMEWORK = "generate_homework_task"
ARQ_TASK_BUILD_PDF = "build_pdf_task"
QUEUE_STUCK_MS = 20_000
WORKER_OFFLINE_ERROR = (
    "Фоновый worker не отвечает. Запустите: arq app.worker_settings.WorkerSettings "
    "(или docker compose up worker). Либо уберите REDIS_URL для режима без worker."
)


class JobQueue:
    """
    Job dispatch:
    - Redis + ARQ worker when REDIS_URL is set (durable, separate process)
    - in-process asyncio fallback otherwise
    """

    def __init__(self) -> None:
        self._lock = asyncio.Lock()
        self._jobs: dict[str, Job] = {}
        self._active_by_key: dict[tuple[int, str], str] = {}
        self._semaphores: dict[int, asyncio.Semaphore] = {}
        self._ai_sem: asyncio.Semaphore | None = None
        self._fallback_runners: dict[str, tuple[tuple[int, str], object]] = {}
        self._reviving: set[str] = set()

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

    def _parse_active_key(self, key: tuple[int, str]) -> tuple[int, str, int]:
        owner_user_id, composite = key
        key_type, key_value_raw = composite.split(":", 1)
        return owner_user_id, key_type, int(key_value_raw)

    def _persist(self, job: Job) -> None:
        job_store.save_job(job)

    def _expire_if_needed(self, job: Job) -> None:
        if job.status not in ("queued", "running"):
            return
        if job.expires_at_ms and self._now_ms() > job.expires_at_ms:
            job.status = "error"
            job.error = "Превышено время ожидания. Попробуйте снова."
            job.updated_at_ms = self._now_ms()
            self._persist(job)

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
                owner_user_id, key_type, key_value = self._parse_active_key(key)
                job_store.clear_active(owner_user_id, key_type, key_value)

    async def _maybe_revive_stuck_job(self, job: Job) -> None:
        if job.status != "queued" or job.id in self._reviving:
            return
        if self._now_ms() - job.created_at_ms < QUEUE_STUCK_MS:
            return
        if is_arq_worker_online():
            return

        payload = self._fallback_runners.get(job.id)
        if not payload:
            job.status = "error"
            job.error = WORKER_OFFLINE_ERROR
            job.updated_at_ms = self._now_ms()
            self._persist(job)
            self._clear_active_for_job(job)
            return

        key, runner = payload
        self._reviving.add(job.id)
        logger.warning("job %s stuck in queue without worker — running in-process", job.id)
        asyncio.create_task(self._run_in_process(job, key, runner))

    async def get(self, job_id: str) -> Job | None:
        async with self._lock:
            self._prune_finished()
            job = self._jobs.get(job_id)
            if job is None:
                job = job_store.load_job(job_id)
                if job is not None:
                    self._jobs[job_id] = job
            if not job:
                return None
            self._expire_if_needed(job)
            if job.status == "error" and job.error and "время ожидания" in job.error:
                self._clear_active_for_job(job)
            return job

        await self._maybe_revive_stuck_job(job)
        return job

    async def _set(self, job: Job) -> None:
        async with self._lock:
            self._jobs[job.id] = job
        self._persist(job)

    async def _find_active_job(self, key: tuple[int, str]) -> Job | None:
        existing_id = self._active_by_key.get(key)
        if not existing_id:
            owner_user_id, key_type, key_value = self._parse_active_key(key)
            existing_id = job_store.get_active(owner_user_id, key_type, key_value)
            if existing_id:
                self._active_by_key[key] = existing_id

        if not existing_id:
            return None

        existing = self._jobs.get(existing_id)
        if existing is None:
            existing = job_store.load_job(existing_id)
            if existing is not None:
                self._jobs[existing_id] = existing
        if not existing:
            return None

        self._expire_if_needed(existing)
        if existing.status in ("queued", "running"):
            return existing
        return None

    async def _run_in_process(self, job: Job, key: tuple[int, str], runner) -> None:
        sem = self._semaphores.setdefault(job.owner_user_id, asyncio.Semaphore(1))
        ai_sem = self._ai_semaphore() if job.type == "generate_homework" else None
        try:
            if ai_sem is not None:
                await ai_sem.acquire()
            async with sem:
                job.status = "running"
                job.updated_at_ms = self._now_ms()
                await self._set(job)
                try:
                    result = await runner()
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
            self._fallback_runners.pop(job.id, None)
            self._reviving.discard(job.id)
            if ai_sem is not None:
                ai_sem.release()
            async with self._lock:
                active = self._active_by_key.get(key)
                if active == job.id:
                    self._active_by_key.pop(key, None)
                    owner_user_id, key_type, key_value = self._parse_active_key(key)
                    job_store.clear_active(owner_user_id, key_type, key_value)

    async def enqueue_unique(
        self,
        *,
        owner_user_id: int,
        key_type: str,
        key_value: int,
        job_type: str,
        arq_task: str,
        arq_args: tuple,
        inprocess_runner,
    ) -> Job:
        key = (owner_user_id, f"{key_type}:{key_value}")
        async with self._lock:
            self._prune_finished()
            existing = await self._find_active_job(key)
            if existing:
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
            if not job_store.set_active(owner_user_id, key_type, key_value, job_id):
                self._jobs.pop(job_id, None)
                self._active_by_key.pop(key, None)
                existing = await self._find_active_job(key)
                if existing:
                    return existing
                peer_id = job_store.get_active(owner_user_id, key_type, key_value)
                if peer_id:
                    peer = job_store.load_job(peer_id) or await self.get(peer_id)
                    if peer is None:
                        peer = job_store.load_job(peer_id)
                        if peer:
                            self._jobs[peer.id] = peer
                    if peer:
                        return peer
                # Stale lock without a loadable job — reclaim.
                job_store.clear_active(owner_user_id, key_type, key_value)
                if not job_store.set_active(owner_user_id, key_type, key_value, job_id):
                    peer_id = job_store.get_active(owner_user_id, key_type, key_value)
                    if peer_id:
                        peer = job_store.load_job(peer_id) or await self.get(peer_id)
                        if peer:
                            self._jobs[peer.id] = peer
                            return peer
                self._jobs[job_id] = job
                self._active_by_key[key] = job_id
            self._persist(job)

        self._fallback_runners[job_id] = (key, inprocess_runner)
        dispatched = await enqueue_arq_task(arq_task, job_id, *arq_args)
        if dispatched:
            logger.info("job %s dispatched to ARQ task=%s", job_id, arq_task)
            return job

        logger.info("job %s running in-process (ARQ/worker unavailable)", job_id)
        asyncio.create_task(self._run_in_process(job, key, inprocess_runner))
        return job


job_queue = JobQueue()
