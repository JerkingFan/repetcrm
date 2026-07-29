from datetime import datetime, date
from typing import Optional

from pydantic import BaseModel, EmailStr, Field, field_validator

from app.password_policy import validate_password_strength
from app.schemas.lessons import LessonOut
from app.schemas.constraints import *  # noqa: F403

class BoardSnapshotOut(BaseModel):
    id: int
    created_at: datetime


class ImportResultOut(BaseModel):
    created: int
    updated: int
    skipped: int
    errors: list[str] = []


class StudentBoundariesOut(BaseModel):
    student_id: int
    student_name: str = ""
    boundary_mode: str
    boundary_reason: str
    boundary_updated_at: Optional[datetime] = None
    suggested_mode: str
    suggested_reason: str
    signals: dict[str, int]
    rules: dict[str, str] = {}
    notification_message: Optional[str] = None


class BoundaryApplyIn(BaseModel):
    mode: str = Field(max_length=20)
    reason: str = Field(default="", max_length=BOUNDARY_REASON_MAX)


class BoundaryMessageOut(BaseModel):
    student_id: int
    student_name: str
    mode: str
    reason: str
    rules: dict[str, str]
    message: str


class BoundarySyncOut(BaseModel):
    previous_mode: str
    new_mode: str
    mode_changed: bool
    escalated: bool
    reason: str
    message: Optional[str] = None


class LessonSeriesOut(BaseModel):
    id: int
    student_id: int
    weekday: int
    lesson_time: str
    duration_minutes: int
    payment_amount: float
    starts_on: date
    until_date: Optional[date] = None
    weeks_ahead: int
    is_active: bool
    lessons_created: int = 0

    class Config:
        from_attributes = True


class LessonCreateResult(BaseModel):
    lesson: LessonOut
    series: Optional[LessonSeriesOut] = None


class LessonWithBoundarySync(BaseModel):
    lesson: LessonOut
    boundary_sync: Optional[BoundarySyncOut] = None



# Boards (Virtual whiteboard)
class BoardCreate(BaseModel):
    title: str = Field(default="Виртуальная доска", max_length=BOARD_TITLE_MAX)


class BoardUpdate(BaseModel):
    title: Optional[str] = Field(default=None, max_length=BOARD_TITLE_MAX)
    state_json: Optional[dict] = None


class BoardOut(BaseModel):
    id: int
    owner_id: int
    title: str
    share_token: str
    state_json: dict
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
