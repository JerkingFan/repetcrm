from datetime import datetime, date
from typing import Optional

from pydantic import BaseModel, EmailStr, Field, field_validator

from app.password_policy import validate_password_strength
from app.schemas.constraints import *  # noqa: F403

class PortalLoginIn(BaseModel):
    portal_token: str = Field(min_length=16, max_length=128)


class PortalStudentOut(BaseModel):
    id: int
    name: str
    display_name: str = ""
    subject: str
    grade: str
    balance: float
    show_balance: bool = False
    tutor_name: str = ""
    tutor_telegram: str = ""
    tutor_contact_url: str = ""
    tutor_telegram_url: str = ""
    portal_nickname: str = ""
    portal_theme: str = "ocean"
    portal_avatar: str = "rocket"


class PortalCustomizeIn(BaseModel):
    portal_nickname: Optional[str] = Field(default=None, max_length=64)
    portal_theme: Optional[str] = Field(default=None, max_length=32)
    portal_avatar: Optional[str] = Field(default=None, max_length=32)


class PortalDailyChallengeOut(BaseModel):
    id: int
    challenge_date: str
    question: str
    topic: str
    difficulty: str = "easy"
    status: str
    answer_text: str = ""
    ai_verdict: str = ""
    ai_score: Optional[int] = None
    ai_feedback: str = ""
    answered_at: Optional[str] = None


class PortalDailyOut(BaseModel):
    available: bool
    reason: str = ""
    message: str = ""
    lesson_today: bool = False
    challenge: Optional[PortalDailyChallengeOut] = None


class PortalDailyAnswerIn(BaseModel):
    answer: str = Field(min_length=1, max_length=2000)


class PortalLessonOut(BaseModel):
    id: int
    lesson_date: date
    lesson_time: str
    duration_minutes: int
    status: str
    is_conducted: bool
    notes: str = ""
    meeting_url: str = ""
    board_id: Optional[int] = None
    board_url: str = ""
    board_title: str = ""
    can_request_reschedule: bool = True
    reschedule_status: str = ""  # pending|approved|rejected|""


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
    due_date: Optional[date] = None
    has_submission: bool
    submission_status: str = "not_submitted"
    updated_at: datetime


class PortalHomeworkDetailOut(BaseModel):
    id: int
    lesson_id: int
    lesson_date: date
    homework_text: str
    preview_html: str = ""
    due_date: Optional[date] = None
    has_submission: bool
    board_url: str = ""
    meeting_url: str = ""
    tutor_telegram_url: str = ""
    submissions: list[HomeworkSubmissionOut] = []


class PortalProgressOut(BaseModel):
    homework_total: int = 0
    homework_submitted: int = 0
    homework_reviewed: int = 0
    homework_needs_revision: int = 0
    streak_days: int = 0
    streak_at_risk: bool = False
    avg_ai_score: Optional[float] = None
    topics: list[str] = []
    topic_heat: list[dict] = []  # {topic, avg_score, samples, level}
    recent_scores: list[dict] = []
    review_hint: str = ""


class LessonVoiceBriefIn(BaseModel):
    brief: str = Field(min_length=3, max_length=2000)
    start_generation: bool = True


class LessonVoiceBriefOut(BaseModel):
    brief: str
    job_id: Optional[str] = None
    status: str = "saved"


class PortalRescheduleIn(BaseModel):
    lesson_id: int
    message: str = Field(default="", max_length=1000)
    preferred_date: Optional[date] = None
    preferred_time: str = Field(default="", max_length=5)


class PortalRescheduleOut(BaseModel):
    id: int
    lesson_id: int
    status: str
    message: str = ""
    preferred_date: Optional[date] = None
    preferred_time: str = ""
    created_at: datetime

    class Config:
        from_attributes = True


class RescheduleRequestOut(BaseModel):
    id: int
    lesson_id: int
    student_id: int
    student_name: str = ""
    lesson_date: date
    lesson_time: str
    message: str = ""
    preferred_date: Optional[date] = None
    preferred_time: str = ""
    status: str
    tutor_note: str = ""
    created_at: datetime


class RescheduleResolveIn(BaseModel):
    status: str = Field(pattern="^(approved|rejected)$")
    tutor_note: str = Field(default="", max_length=1000)


class PortalLinkOut(BaseModel):
    portal_token: str
    portal_url: str
