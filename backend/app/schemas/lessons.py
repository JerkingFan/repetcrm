from datetime import datetime, date
from typing import Optional

from pydantic import BaseModel, EmailStr, Field, field_validator

from app.password_policy import validate_password_strength
from app.schemas.checklist import ChecklistItemOut, HomeworkPrefs
from app.schemas.constraints import *  # noqa: F403

class LessonRecurrenceIn(BaseModel):
    weekday: int = Field(ge=0, le=6, description="0=Monday .. 6=Sunday")
    weeks_ahead: int = Field(default=8, ge=1, le=52)
    until_date: Optional[date] = None


class LessonCreate(BaseModel):
    student_id: int
    lesson_date: date
    lesson_time: str = Field(default="10:00", max_length=5)
    duration_minutes: int = Field(default=60, ge=1, le=480)
    payment_amount: float = Field(default=0.0, ge=0)
    is_paid: bool = False
    notes: str = Field(default="", max_length=NOTES_MAX)
    meeting_url: str = Field(default="", max_length=MEETING_URL_MAX)
    is_trial: bool = False
    recurrence: Optional[LessonRecurrenceIn] = None


class LessonUpdate(BaseModel):
    lesson_date: Optional[date] = None
    lesson_time: Optional[str] = Field(default=None, max_length=5)
    duration_minutes: Optional[int] = Field(default=None, ge=1, le=480)
    payment_amount: Optional[float] = Field(default=None, ge=0)
    is_paid: Optional[bool] = None
    status: Optional[str] = Field(default=None, max_length=20)
    late_minutes: Optional[int] = Field(default=None, ge=0)
    rescheduled_from_lesson_id: Optional[int] = None
    notes: Optional[str] = Field(default=None, max_length=NOTES_MAX)
    meeting_url: Optional[str] = Field(default=None, max_length=MEETING_URL_MAX)


class HomeworkBrief(BaseModel):
    id: int
    homework_text: str
    due_date: Optional[date] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class LessonOut(BaseModel):
    id: int
    student_id: int
    board_id: Optional[int] = None
    series_id: Optional[int] = None
    lesson_date: date
    lesson_time: str = "10:00"
    duration_minutes: int
    payment_amount: float
    is_paid: bool
    is_conducted: bool = False
    status: str = "scheduled"
    late_minutes: int = 0
    rescheduled_from_lesson_id: Optional[int] = None
    homework_prefs: Optional[HomeworkPrefs] = None
    notes: str
    meeting_url: str = ""
    created_at: datetime
    student_name: Optional[str] = None
    checklist_items: list[ChecklistItemOut] = []
    homework: Optional[HomeworkBrief] = None

    class Config:
        from_attributes = True


class LessonListItem(BaseModel):
    """Краткая запись для календаря/списка (без чек-листа, prefs и текста ДЗ)."""

    id: int
    student_id: int
    board_id: Optional[int] = None
    lesson_date: date
    lesson_time: str = "10:00"
    duration_minutes: int
    payment_amount: float
    is_paid: bool
    is_conducted: bool = False
    status: str = "scheduled"
    notes: str = ""
    meeting_url: str = ""
    student_name: Optional[str] = None
    homework_id: Optional[int] = None
