from __future__ import annotations

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
    expires_at_ms: int = 0
