from datetime import datetime, date
from typing import Optional

from pydantic import BaseModel, EmailStr, Field, field_validator

from app.password_policy import validate_password_strength
from app.schemas.constraints import *  # noqa: F403

class DashboardStats(BaseModel):
    students_count: int
    lessons_this_month: int
    payments_this_month: float
    unpaid_total: float


class DashboardLessonBrief(BaseModel):
    id: int
    lesson_date: date
    lesson_time: str
    student_id: int
    student_name: str
    duration_minutes: int
    is_paid: bool
    payment_amount: float
    meeting_url: str = ""


class DashboardDebtItem(BaseModel):
    student_id: int
    student_name: str
    unpaid_amount: float
    unpaid_lessons: int


class DashboardInactiveStudent(BaseModel):
    student_id: int
    student_name: str
    last_lesson_date: Optional[date] = None
    days_since: Optional[int] = None


class DashboardOverdueHomework(BaseModel):
    lesson_id: int
    lesson_date: date
    student_id: int
    student_name: str
    days_since: int


class DashboardExtended(BaseModel):
    stats: DashboardStats
    upcoming_lessons: list[DashboardLessonBrief] = []
    debtors: list[DashboardDebtItem] = []
    inactive_students: list[DashboardInactiveStudent] = []
    overdue_homework: list[DashboardOverdueHomework] = []
    trial_lessons_this_week: list["DashboardTrialLesson"] = []
    trial_followups: list["DashboardTrialFollowup"] = []
    pending_payment_receipts: list["DashboardPendingReceipt"] = []


class DashboardTrialLesson(BaseModel):
    lesson_id: int
    student_id: int
    student_name: str
    lesson_date: date
    lesson_time: str
    is_conducted: bool
    student_status: str
    conducted_lessons: int


class DashboardTrialFollowup(BaseModel):
    student_id: int
    student_name: str
    parent_name: str
    conducted_lessons: int
    message: str


class TrialFollowupOut(BaseModel):
    show: bool
    message: str
    parent_portal_url: str
    student_name: str
    conducted_lessons: int


class PaymentRequisitesOut(BaseModel):
    payment_details: str


class PaymentRequisitesUpdate(BaseModel):
    payment_details: str = Field(max_length=4000)


class ParentPaymentDetailsOut(BaseModel):
    tutor_name: str
    payment_details: str
    has_requisites: bool


class PaymentReceiptOut(BaseModel):
    id: int
    student_id: int
    student_name: str = ""
    amount: float
    status: str
    original_filename: str
    parent_note: str
    tutor_note: str
    created_at: datetime
    reviewed_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class DashboardPendingReceipt(BaseModel):
    id: int
    student_id: int
    student_name: str
    amount: float
    original_filename: str
    parent_note: str
    created_at: datetime


class PaymentReceiptReviewIn(BaseModel):
    tutor_note: str = Field(default="", max_length=2000)


class QuickConductOut(BaseModel):
    lesson_id: int
    is_conducted: bool
    trial_followup: TrialFollowupOut | None = None


class StudentHomeworkItem(BaseModel):
    id: int
    lesson_id: int
    lesson_date: date
    preview: str
    created_at: datetime
    updated_at: datetime


class StudentHomeworkPage(BaseModel):
    items: list[StudentHomeworkItem]
    total: int
    page: int
    page_size: int
    has_more: bool
