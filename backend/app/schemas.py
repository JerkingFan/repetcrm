from datetime import datetime, date
from typing import Optional

from pydantic import BaseModel, EmailStr, Field


# Auth
class UserRegister(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6)
    name: str = ""


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


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
    notes: str = ""


class StudentUpdate(BaseModel):
    name: Optional[str] = None
    subject: Optional[str] = None
    grade: Optional[str] = None
    school: Optional[str] = None
    contact: Optional[str] = None
    parent_contact: Optional[str] = None
    notes: Optional[str] = None


class StudentOut(BaseModel):
    id: int
    name: str
    subject: str
    grade: str
    school: str
    contact: str
    parent_contact: str
    notes: str
    boundary_mode: str = "normal"
    boundary_reason: str = ""
    boundary_updated_at: Optional[datetime] = None
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
class LessonCreate(BaseModel):
    student_id: int
    lesson_date: date
    lesson_time: str = "10:00"
    duration_minutes: int = 60
    payment_amount: float = 0.0
    is_paid: bool = False
    notes: str = ""


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


class StudentWithLessons(StudentOut):
    lessons: list[LessonOut] = []


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
