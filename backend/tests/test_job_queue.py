"""In-process job queue lifecycle (no Redis)."""

import asyncio

import pytest

from app.services.job_queue import JobQueue


@pytest.mark.asyncio
async def test_job_queue_enqueue_and_status():
    queue = JobQueue()

    async def runner():
        return {"ok": True}

    job = await queue.enqueue_unique(
        owner_user_id=1,
        key_type="lesson",
        key_value=42,
        job_type="generate_homework",
        arq_task="generate_homework_task",
        arq_args=(42, 1),
        inprocess_runner=runner,
    )
    assert job.owner_user_id == 1
    assert job.lesson_id == 42

    loaded = await queue.get(job.id)
    assert loaded is not None
    assert loaded.id == job.id

    for _ in range(20):
        await asyncio.sleep(0.05)
        final = await queue.get(job.id)
        if final and final.status == "done":
            assert final.result == {"ok": True}
            return
    pytest.fail("job did not complete in time")
