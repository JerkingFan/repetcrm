from datetime import datetime, date
from typing import Optional

from pydantic import BaseModel, EmailStr, Field, field_validator

from app.password_policy import validate_password_strength
from app.schemas.constraints import *  # noqa: F403

class ParentPortalLoginIn(BaseModel):
    parent_portal_token: str = Field(min_length=16, max_length=128)


class ParentPortalLinkOut(BaseModel):
    parent_portal_token: str
    parent_portal_url: str


class ParentPortalOut(BaseModel):
    student_id: int
    student_name: str
    subject: str
    grade: str
    parent_name: str
    balance: float
    tutor_name: str = ""
    tutor_telegram_url: str = ""


class ParentRescheduleIn(BaseModel):
    lesson_id: int
    message: str = Field(default="", max_length=1000)
    preferred_date: Optional[date] = None
    preferred_time: str = Field(default="", max_length=5)


class ParentPortalPackageOut(BaseModel):
    id: int
    name: str
    lessons_total: int
    lessons_remaining: int
    price_per_lesson: float
    is_active: bool

    class Config:
        from_attributes = True


class ParentHomeworkStatusOut(BaseModel):
    homework_id: int
    lesson_id: int
    lesson_date: date
    status: str
    status_label: str
    reviewed_at: Optional[datetime] = None


class ParentReportLessonItem(BaseModel):
    lesson_date: date
    lesson_time: str
    is_conducted: bool
    is_paid: bool
    payment_amount: float


class ParentReportHomeworkItem(BaseModel):
    lesson_date: date
    status: str
    status_label: str


class ParentMonthlyReportOut(BaseModel):
    month: str
    month_label: str
    student_name: str
    tutor_name: str
    subject: str
    grade: str
    lessons_total: int
    lessons_conducted: int
    lessons: list[ParentReportLessonItem]
    homework: list[ParentReportHomeworkItem]
    topics_covered: list[str]
    payments_total: float
    balance: float
    homework_total: int = 0
    homework_done_pct: int = 0
    tutor_note: str = ""
    snapshot_line: str = ""
