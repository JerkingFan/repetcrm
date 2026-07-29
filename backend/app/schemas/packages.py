from datetime import datetime, date
from typing import Optional

from pydantic import BaseModel, EmailStr, Field, field_validator

from app.password_policy import validate_password_strength
from app.schemas.checklist import ChecklistItemCreate, ChecklistItemOut, HomeworkPrefs
from app.schemas.constraints import *  # noqa: F403

class PortalPaymentIntentIn(BaseModel):
    amount: float = Field(gt=0)
    provider: str = Field(pattern="^(erip|card)$")


class LessonPackageCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    lessons_total: int = Field(ge=1, le=500)
    price_per_lesson: float = Field(ge=0)
    prepaid_amount: float = Field(default=0, ge=0)


class LessonPackageOut(BaseModel):
    id: int
    student_id: int
    name: str
    lessons_total: int
    lessons_remaining: int
    price_per_lesson: float
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


class StudentBalanceTopUp(BaseModel):
    amount: float = Field(gt=0)


class HomeworkTemplateCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    subject: str = ""
    homework_text: str = ""
    homework_prefs: HomeworkPrefs = Field(default_factory=HomeworkPrefs)
    checklist_items: list[ChecklistItemCreate] = Field(default_factory=list)


class HomeworkTemplateUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    subject: Optional[str] = None
    homework_text: Optional[str] = None
    homework_prefs: Optional[HomeworkPrefs] = None
    checklist_items: Optional[list[ChecklistItemCreate]] = None


class HomeworkTemplateFromLessonIn(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    include_homework_text: bool = True


class HomeworkTemplateOut(BaseModel):
    id: int
    name: str
    subject: str
    homework_text: str
    homework_prefs: HomeworkPrefs
    checklist_items: list[ChecklistItemOut]
    source_lesson_id: Optional[int] = None
    preview: str = ""
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ApplyHomeworkTemplateIn(BaseModel):
    copy_homework_text: bool = True


class PaymentIntentCreate(BaseModel):
    student_id: int
    amount: float = Field(gt=0)
    provider: str = Field(pattern="^(erip|card)$")
    purpose: str = "balance_topup"
    purpose_ref_id: Optional[int] = None


class PaymentIntentOut(BaseModel):
    id: int
    student_id: int
    amount: float
    currency: str
    provider: str
    status: str
    purpose: str
    erip_code: Optional[str] = None
    payment_url: Optional[str] = None
    public_token: str
    expires_at: datetime
    paid_at: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True


class PaymentPublicOut(BaseModel):
    id: int
    amount: float
    currency: str
    provider: str
    status: str
    erip_code: Optional[str] = None
    student_name: str
    expires_at: datetime


class PaymentWebhookIn(BaseModel):
    intent_id: int
    external_id: str
    status: str = "paid"


class AnalyticsRevenueMonth(BaseModel):
    month: str
    revenue: float
    paid_lessons: int


class AnalyticsTrialConversion(BaseModel):
    period_days: int
    students_with_trial_lesson: int
    students_converted: int
    students_with_any_lesson: int
    conversion_rate_percent: float


class AnalyticsChurnOut(BaseModel):
    inactive_days_threshold: int
    churned_students: int
    at_risk_students: int
    active_last_90_days: int
    churn_rate_percent: float


class AnalyticsOverview(BaseModel):
    revenue_by_month: list[AnalyticsRevenueMonth]
    trial_conversion: AnalyticsTrialConversion
    churn: AnalyticsChurnOut


class PromptTemplateOut(BaseModel):
    id: int
    title: str
    description: str
    subject: str
    grade: str
    homework_prefs: HomeworkPrefs
    checklist_items: list[ChecklistItemOut]
    use_count: int
    installed: bool = False
    created_at: datetime

    class Config:
        from_attributes = True


class PromptTemplateInstallOut(BaseModel):
    template_id: int
    homework_template_id: int
    message: str
