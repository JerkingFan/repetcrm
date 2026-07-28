from datetime import datetime, date
from typing import Optional

from pydantic import BaseModel, EmailStr, Field, field_validator

from app.password_policy import validate_password_strength


# Auth
class UserRegister(BaseModel):
    email: EmailStr
    password: str = Field(min_length=10, max_length=128)
    name: str = ""

    @field_validator("password")
    @classmethod
    def password_strength(cls, value: str) -> str:
        return validate_password_strength(value)


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class ForgotPasswordIn(BaseModel):
    email: EmailStr


class ResetPasswordIn(BaseModel):
    token: str = Field(min_length=16, max_length=256)
    password: str = Field(min_length=10, max_length=128)

    @field_validator("password")
    @classmethod
    def password_strength(cls, value: str) -> str:
        return validate_password_strength(value)


class ChangePasswordIn(BaseModel):
    current_password: str
    new_password: str = Field(min_length=10, max_length=128)

    @field_validator("new_password")
    @classmethod
    def password_strength(cls, value: str) -> str:
        return validate_password_strength(value)


class NotificationSettingsOut(BaseModel):
    notify_email: bool
    notify_telegram: bool
    notify_lesson_tomorrow: bool
    notify_unpaid: bool
    notify_homework_ready: bool
    telegram_chat_id: str
    smtp_configured: bool = False
    telegram_configured: bool = False


class NotificationSettingsUpdate(BaseModel):
    notify_email: Optional[bool] = None
    notify_telegram: Optional[bool] = None
    notify_lesson_tomorrow: Optional[bool] = None
    notify_unpaid: Optional[bool] = None
    notify_homework_ready: Optional[bool] = None
    telegram_chat_id: Optional[str] = None


class MessageOut(BaseModel):
    message: str


class Token(BaseModel):
    access_token: str = ""
    token_type: str = "cookie"


class UserOut(BaseModel):
    id: int
    email: str
    name: str
    onboarding_completed: bool = False
    subjects: list[str] = []
    grade_levels: list[str] = []
    teaching_format: str = ""

    class Config:
        from_attributes = True


class OnboardingComplete(BaseModel):
    subjects: list[str] = Field(min_length=1)
    grade_levels: list[str] = Field(min_length=1)
    teaching_format: str = ""


class OnboardingUpdate(BaseModel):
    subjects: Optional[list[str]] = None
    grade_levels: Optional[list[str]] = None
    teaching_format: Optional[str] = None


# Students
class StudentCreate(BaseModel):
    name: str
    subject: str = ""
    grade: str = ""
    school: str = ""
    contact: str = ""
    parent_contact: str = ""
    parent_name: str = ""
    parent_email: str = ""
    parent_phone: str = ""
    parent_notify_email: bool = True
    notes: str = ""


class StudentUpdate(BaseModel):
    name: Optional[str] = None
    subject: Optional[str] = None
    grade: Optional[str] = None
    school: Optional[str] = None
    contact: Optional[str] = None
    parent_contact: Optional[str] = None
    parent_name: Optional[str] = None
    parent_email: Optional[str] = None
    parent_phone: Optional[str] = None
    parent_notify_email: Optional[bool] = None
    notes: Optional[str] = None


class StudentOut(BaseModel):
    id: int
    name: str
    subject: str
    grade: str
    school: str
    contact: str
    parent_contact: str
    parent_name: str = ""
    parent_email: str = ""
    parent_phone: str = ""
    parent_notify_email: bool = True
    notes: str
    boundary_mode: str = "normal"
    boundary_reason: str = ""
    boundary_updated_at: Optional[datetime] = None
    balance: float = 0.0
    created_at: datetime

    class Config:
        from_attributes = True


class StudentListItem(BaseModel):
    """Краткая карточка для списка (без boundary и created_at)."""

    id: int
    name: str
    subject: str
    grade: str
    school: str
    contact: str
    parent_contact: str
    parent_name: str = ""
    parent_email: str = ""
    parent_phone: str = ""
    notes: str

    class Config:
        from_attributes = True


class StudentListPage(BaseModel):
    items: list[StudentListItem]
    total: int
    page: int
    page_size: int
    has_more: bool


# Checklist
class ChecklistItemCreate(BaseModel):
    topic: str
    work_type: str = "practice"
    difficulty: str = "medium"
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
    special_notes: str = ""
    output_formats: list[str] = Field(default_factory=lambda: ["latex"])
    include_cheatsheet: bool = False
    include_hints: bool = False
    include_examples: bool = False


class LessonReportCreate(BaseModel):
    """Чек-лист тем + настройки ДЗ после проведённого занятия."""
    items: list[ChecklistItemCreate] = Field(min_length=1)
    prefs: HomeworkPrefs = Field(default_factory=HomeworkPrefs)
    is_conducted: bool = True


# Lessons
class LessonRecurrenceIn(BaseModel):
    weekday: int = Field(ge=0, le=6, description="0=Monday .. 6=Sunday")
    weeks_ahead: int = Field(default=8, ge=1, le=52)
    until_date: Optional[date] = None


class LessonCreate(BaseModel):
    student_id: int
    lesson_date: date
    lesson_time: str = "10:00"
    duration_minutes: int = 60
    payment_amount: float = 0.0
    is_paid: bool = False
    notes: str = ""
    recurrence: Optional[LessonRecurrenceIn] = None


class LessonUpdate(BaseModel):
    lesson_date: Optional[date] = None
    lesson_time: Optional[str] = None
    duration_minutes: Optional[int] = None
    payment_amount: Optional[float] = None
    is_paid: Optional[bool] = None
    status: Optional[str] = None
    late_minutes: Optional[int] = None
    rescheduled_from_lesson_id: Optional[int] = None
    notes: Optional[str] = None


class HomeworkBrief(BaseModel):
    id: int
    homework_text: str
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
    student_name: Optional[str] = None
    homework_id: Optional[int] = None


# Homework
class HomeworkUpdate(BaseModel):
    homework_text: str


class HomeworkOut(BaseModel):
    id: int
    lesson_id: int
    homework_text: str
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


# Dashboard
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
    mode: str
    reason: str = ""


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
    title: str = "Виртуальная доска"


class BoardUpdate(BaseModel):
    title: Optional[str] = None
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


# Student portal
class PortalLoginIn(BaseModel):
    portal_token: str = Field(min_length=16, max_length=128)


class PortalStudentOut(BaseModel):
    id: int
    name: str
    subject: str
    grade: str
    balance: float
    tutor_name: str = ""


class PortalLessonOut(BaseModel):
    id: int
    lesson_date: date
    lesson_time: str
    duration_minutes: int
    status: str
    is_conducted: bool
    notes: str = ""


class HomeworkSubmissionOut(BaseModel):
    id: int
    homework_id: int
    original_filename: str
    mime_type: str
    comment: str
    status: str = "submitted"
    tutor_comment: str = ""
    reviewed_at: Optional[datetime] = None
    ai_review_status: str = "pending"
    ai_verdict: str = ""
    ai_score: Optional[int] = None
    ai_feedback: str = ""
    ai_review_error: str = ""
    ai_reviewed_at: Optional[datetime] = None
    submitted_at: datetime

    class Config:
        from_attributes = True


class HomeworkSubmissionReviewIn(BaseModel):
    status: str = Field(pattern="^(reviewed|needs_revision)$")
    tutor_comment: str = Field(default="", max_length=2000)


class PortalHomeworkOut(BaseModel):
    id: int
    lesson_id: int
    lesson_date: date
    preview: str
    tasks_count: int = 0
    has_submission: bool
    submission_status: str = "not_submitted"
    updated_at: datetime


class PortalHomeworkDetailOut(BaseModel):
    id: int
    lesson_id: int
    lesson_date: date
    homework_text: str
    preview_html: str = ""
    has_submission: bool
    submissions: list[HomeworkSubmissionOut] = []


class PortalLinkOut(BaseModel):
    portal_token: str
    portal_url: str


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


# Public trial booking
class BookingHoursSlot(BaseModel):
    weekday: int = Field(ge=0, le=6)
    from_time: str = "10:00"
    to_time: str = "18:00"


class BookingSlotOut(BaseModel):
    date: date
    time: str
    label: str


class BookingTutorPublicOut(BaseModel):
    tutor_name: str
    subjects: list[str] = []
    grade_levels: list[str] = []
    teaching_format: str = ""
    slots: list[BookingSlotOut] = []


class TrialBookingSubmitIn(BaseModel):
    child_name: str = Field(min_length=1, max_length=255)
    grade: str = Field(max_length=50)
    subject: str = Field(max_length=255)
    parent_name: str = Field(min_length=1, max_length=255)
    parent_email: str = Field(min_length=3, max_length=255)
    parent_phone: str = Field(default="", max_length=64)
    preferred_date: date
    preferred_time: str = Field(pattern=r"^\d{2}:\d{2}$")
    message: str = Field(default="", max_length=2000)


class TrialBookingSubmitOut(BaseModel):
    message: str
    booking_id: int


class BookingSettingsOut(BaseModel):
    booking_slug: str
    booking_enabled: bool
    booking_hours: list[BookingHoursSlot]
    booking_reply_text: str
    booking_url: str


class BookingSettingsUpdate(BaseModel):
    booking_slug: Optional[str] = None
    booking_enabled: Optional[bool] = None
    booking_hours: Optional[list[BookingHoursSlot]] = None
    booking_reply_text: Optional[str] = None


class TrialBookingLeadOut(BaseModel):
    id: int
    student_id: int
    child_name: str
    grade: str
    subject: str
    parent_name: str
    parent_email: str
    parent_phone: str
    preferred_date: date
    preferred_time: str
    parent_message: str
    status: str
    created_at: datetime

    class Config:
        from_attributes = True

