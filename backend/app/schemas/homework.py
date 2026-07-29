from datetime import datetime, date
from typing import Optional

from pydantic import BaseModel, EmailStr, Field, field_validator

from app.password_policy import validate_password_strength
from app.schemas.constraints import *  # noqa: F403

class HomeworkUpdate(BaseModel):
    homework_text: Optional[str] = None
    due_date: Optional[date] = None


class HomeworkOut(BaseModel):
    id: int
    lesson_id: int
    homework_text: str
    due_date: Optional[date] = None
    created_at: datetime
    updated_at: datetime
    student_name: Optional[str] = None
    lesson_date: Optional[date] = None
    generation_source: Optional[str] = None
    generation_hint: Optional[str] = None
    configured_provider: Optional[str] = None
    configured_model: Optional[str] = None

    class Config:
        from_attributes = True


class HomeworkJobStartOut(BaseModel):
    job_id: str
    status: str


class HomeworkJobOut(BaseModel):
    job_id: str
    status: str
    lesson_id: int | None = None
    homework_id: int | None = None
    job_type: str | None = None
    created_at_ms: int
    updated_at_ms: int
    result: dict | None = None
    error: str | None = None


class StudentLessonHistoryItem(BaseModel):
    id: int
    lesson_date: date
    homework_id: Optional[int] = None


class StudentLessonsPage(BaseModel):
    items: list[StudentLessonHistoryItem]
    total: int
    page: int
    page_size: int
    has_more: bool
