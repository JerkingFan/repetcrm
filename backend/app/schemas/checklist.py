from datetime import datetime, date
from typing import Optional

from pydantic import BaseModel, EmailStr, Field, field_validator

from app.password_policy import validate_password_strength
from app.schemas.constraints import *  # noqa: F403

class ChecklistItemCreate(BaseModel):
    topic: str = Field(min_length=1, max_length=TOPIC_MAX)
    work_type: str = Field(default="practice", max_length=50)
    difficulty: str = Field(default="medium", max_length=50)
    understanding: int = Field(ge=1, le=5, default=3)


class ChecklistItemOut(ChecklistItemCreate):
    id: int

    class Config:
        from_attributes = True


class ChecklistBulkCreate(BaseModel):
    items: list[ChecklistItemCreate]


class HomeworkPrefs(BaseModel):
    focus_aspect: str = "mixed"
    student_level: str = "medium"
    understanding_global: int = Field(ge=1, le=5, default=3)
    task_types: list[str] = Field(default_factory=lambda: ["practice_rules", "text_problems"])
    volume: str = "standard"
    difficulty_level: str = "medium"
    special_notes: str = Field(default="", max_length=SPECIAL_NOTES_MAX)
    output_formats: list[str] = Field(default_factory=lambda: ["latex"])
    include_cheatsheet: bool = False
    include_hints: bool = False
    include_examples: bool = False


class LessonReportCreate(BaseModel):
    """Чек-лист тем + настройки ДЗ после проведённого занятия."""
    items: list[ChecklistItemCreate] = Field(min_length=1)
    prefs: HomeworkPrefs = Field(default_factory=HomeworkPrefs)
    is_conducted: bool = True
