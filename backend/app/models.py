from datetime import datetime, date

from sqlalchemy import String, Integer, Float, Boolean, ForeignKey, DateTime, Date, Text, Enum as SAEnum, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
import enum

from app.database import Base


class WorkType(str, enum.Enum):
    theory = "theory"
    practice = "practice"
    test = "test"


class Difficulty(str, enum.Enum):
    basic = "basic"
    medium = "medium"
    advanced = "advanced"


class LessonStatus(str, enum.Enum):
    scheduled = "scheduled"
    completed = "completed"
    cancelled = "cancelled"
    no_show = "no_show"
    rescheduled = "rescheduled"


class StudentBoundaryMode(str, enum.Enum):
    normal = "normal"
    yellow = "yellow"
    orange = "orange"
    red = "red"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255))
    name: Mapped[str] = mapped_column(String(255), default="")
    onboarding_completed: Mapped[bool] = mapped_column(Boolean, default=False)
    subjects: Mapped[str] = mapped_column(Text, default="[]")
    grade_levels: Mapped[str] = mapped_column(Text, default="[]")
    teaching_format: Mapped[str] = mapped_column(String(50), default="")
    telegram_chat_id: Mapped[str] = mapped_column(String(64), default="")
    notify_email: Mapped[bool] = mapped_column(Boolean, default=True)
    notify_telegram: Mapped[bool] = mapped_column(Boolean, default=False)
    notify_lesson_tomorrow: Mapped[bool] = mapped_column(Boolean, default=True)
    notify_unpaid: Mapped[bool] = mapped_column(Boolean, default=True)
    notify_homework_ready: Mapped[bool] = mapped_column(Boolean, default=True)
    booking_slug: Mapped[str | None] = mapped_column(String(64), unique=True, index=True, nullable=True)
    booking_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    booking_hours: Mapped[str] = mapped_column(Text, default="[]")
    booking_reply_text: Mapped[str] = mapped_column(Text, default="")
    payment_details: Mapped[str] = mapped_column(Text, default="")
    contact_telegram: Mapped[str] = mapped_column(String(64), default="")
    contact_url: Mapped[str] = mapped_column(String(500), default="")
    hide_balance_in_portal: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    students: Mapped[list["Student"]] = relationship(back_populates="tutor")
    lessons: Mapped[list["Lesson"]] = relationship(back_populates="tutor")
    trial_bookings: Mapped[list["TrialBooking"]] = relationship(back_populates="tutor")
    auth_sessions: Mapped[list["AuthSession"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    password_reset_tokens: Mapped[list["PasswordResetToken"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )


class PasswordResetToken(Base):
    __tablename__ = "password_reset_tokens"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime)
    used_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    user: Mapped["User"] = relationship(back_populates="password_reset_tokens")


class AuthSession(Base):
    __tablename__ = "auth_sessions"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    last_ip: Mapped[str] = mapped_column(String(45), default="")
    user_agent: Mapped[str] = mapped_column(String(512), default="")

    user: Mapped["User"] = relationship(back_populates="auth_sessions")


class Student(Base):
    __tablename__ = "students"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    tutor_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    name: Mapped[str] = mapped_column(String(255))
    subject: Mapped[str] = mapped_column(String(255), default="")
    grade: Mapped[str] = mapped_column(String(50), default="")
    school: Mapped[str] = mapped_column(String(255), default="")
    contact: Mapped[str] = mapped_column(String(255), default="")
    parent_contact: Mapped[str] = mapped_column(String(255), default="")
    parent_name: Mapped[str] = mapped_column(String(255), default="")
    parent_email: Mapped[str] = mapped_column(String(255), default="")
    parent_phone: Mapped[str] = mapped_column(String(64), default="")
    parent_notify_email: Mapped[bool] = mapped_column(Boolean, default=True)
    notes: Mapped[str] = mapped_column(Text, default="")
    boundary_mode: Mapped[str] = mapped_column(String(20), default=StudentBoundaryMode.normal.value)
    boundary_reason: Mapped[str] = mapped_column(Text, default="")
    boundary_updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    portal_token: Mapped[str | None] = mapped_column(String(64), unique=True, index=True, nullable=True)
    parent_portal_token: Mapped[str | None] = mapped_column(String(64), unique=True, index=True, nullable=True)
    balance: Mapped[float] = mapped_column(Float, default=0.0)
    first_lesson_at: Mapped[date | None] = mapped_column(Date, nullable=True)
    last_lesson_at: Mapped[date | None] = mapped_column(Date, nullable=True)
    student_status: Mapped[str] = mapped_column(String(20), default="active")
    portal_nickname: Mapped[str] = mapped_column(String(64), default="")
    portal_theme: Mapped[str] = mapped_column(String(32), default="ocean")
    portal_avatar: Mapped[str] = mapped_column(String(32), default="rocket")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    tutor: Mapped["User"] = relationship(back_populates="students")
    lessons: Mapped[list["Lesson"]] = relationship(back_populates="student")
    packages: Mapped[list["LessonPackage"]] = relationship(back_populates="student")
    trial_bookings: Mapped[list["TrialBooking"]] = relationship(back_populates="student")
    daily_challenges: Mapped[list["StudentDailyChallenge"]] = relationship(
        back_populates="student", cascade="all, delete-orphan"
    )


class HomeworkTemplate(Base):
    __tablename__ = "homework_templates"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    tutor_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(255), default="")
    subject: Mapped[str] = mapped_column(String(255), default="")
    homework_text: Mapped[str] = mapped_column(Text, default="")
    homework_prefs: Mapped[str] = mapped_column(Text, default="")
    checklist_json: Mapped[str] = mapped_column(Text, default="[]")
    source_lesson_id: Mapped[int | None] = mapped_column(
        ForeignKey("lessons.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    tutor: Mapped["User"] = relationship()


class PaymentIntent(Base):
    __tablename__ = "payment_intents"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    tutor_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("students.id", ondelete="CASCADE"), index=True)
    amount: Mapped[float] = mapped_column(Float)
    currency: Mapped[str] = mapped_column(String(3), default="BYN")
    purpose: Mapped[str] = mapped_column(String(30), default="balance_topup")
    purpose_ref_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    provider: Mapped[str] = mapped_column(String(20))
    status: Mapped[str] = mapped_column(String(20), default="pending")
    public_token: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    external_order_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    erip_code: Mapped[str | None] = mapped_column(String(32), nullable=True)
    payment_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime)
    paid_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    student: Mapped["Student"] = relationship()
    tutor: Mapped["User"] = relationship()


class PaymentTransaction(Base):
    __tablename__ = "payment_transactions"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    intent_id: Mapped[int | None] = mapped_column(
        ForeignKey("payment_intents.id", ondelete="SET NULL"), nullable=True
    )
    tutor_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    student_id: Mapped[int] = mapped_column(ForeignKey("students.id", ondelete="CASCADE"))
    amount: Mapped[float] = mapped_column(Float)
    currency: Mapped[str] = mapped_column(String(3), default="BYN")
    provider: Mapped[str] = mapped_column(String(20))
    external_id: Mapped[str] = mapped_column(String(128))
    status: Mapped[str] = mapped_column(String(20), default="paid")
    raw_payload: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class PromptTemplate(Base):
    __tablename__ = "prompt_templates"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    author_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    title: Mapped[str] = mapped_column(String(255))
    description: Mapped[str] = mapped_column(Text, default="")
    subject: Mapped[str] = mapped_column(String(255), default="", index=True)
    grade: Mapped[str] = mapped_column(String(50), default="", index=True)
    homework_prefs: Mapped[str] = mapped_column(Text, default="")
    checklist_json: Mapped[str] = mapped_column(Text, default="[]")
    sample_homework_text: Mapped[str] = mapped_column(Text, default="")
    visibility: Mapped[str] = mapped_column(String(20), default="public")
    use_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )


class PromptTemplateInstall(Base):
    __tablename__ = "prompt_template_installs"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    tutor_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    template_id: Mapped[int] = mapped_column(ForeignKey("prompt_templates.id", ondelete="CASCADE"))
    homework_template_id: Mapped[int | None] = mapped_column(
        ForeignKey("homework_templates.id", ondelete="SET NULL"), nullable=True
    )
    installed_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class Lesson(Base):
    __tablename__ = "lessons"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    tutor_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    student_id: Mapped[int] = mapped_column(ForeignKey("students.id"))
    board_id: Mapped[int | None] = mapped_column(ForeignKey("boards.id"), nullable=True)
    lesson_date: Mapped[date] = mapped_column(Date)
    lesson_time: Mapped[str] = mapped_column(String(5), default="10:00")
    duration_minutes: Mapped[int] = mapped_column(Integer, default=60)
    payment_amount: Mapped[float] = mapped_column(Float, default=0.0)
    is_paid: Mapped[bool] = mapped_column(Boolean, default=False)
    paid_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    payment_source: Mapped[str | None] = mapped_column(String(30), nullable=True)
    is_conducted: Mapped[bool] = mapped_column(Boolean, default=False)
    status: Mapped[str] = mapped_column(String(20), default=LessonStatus.scheduled.value)
    late_minutes: Mapped[int] = mapped_column(Integer, default=0)
    rescheduled_from_lesson_id: Mapped[int | None] = mapped_column(
        ForeignKey("lessons.id"), nullable=True
    )
    status_changed_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    homework_prefs: Mapped[str] = mapped_column(Text, default="")
    notes: Mapped[str] = mapped_column(Text, default="")
    meeting_url: Mapped[str] = mapped_column(String(500), default="")
    series_id: Mapped[int | None] = mapped_column(ForeignKey("lesson_series.id"), nullable=True, index=True)
    package_id: Mapped[int | None] = mapped_column(ForeignKey("lesson_packages.id"), nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    tutor: Mapped["User"] = relationship(back_populates="lessons")
    student: Mapped["Student"] = relationship(back_populates="lessons")
    board: Mapped["Board | None"] = relationship()
    rescheduled_from: Mapped["Lesson | None"] = relationship(remote_side="Lesson.id")
    checklist_items: Mapped[list["ChecklistItem"]] = relationship(
        back_populates="lesson", cascade="all, delete-orphan"
    )
    homework: Mapped["Homework | None"] = relationship(
        back_populates="lesson", uselist=False, cascade="all, delete-orphan"
    )
    series: Mapped["LessonSeries | None"] = relationship(back_populates="lessons")
    package: Mapped["LessonPackage | None"] = relationship(back_populates="lessons")


class ChecklistItem(Base):
    __tablename__ = "checklist_items"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    lesson_id: Mapped[int] = mapped_column(ForeignKey("lessons.id"))
    topic: Mapped[str] = mapped_column(String(500))
    work_type: Mapped[str] = mapped_column(String(50), default=WorkType.practice.value)
    difficulty: Mapped[str] = mapped_column(String(50), default=Difficulty.medium.value)
    understanding: Mapped[int] = mapped_column(Integer, default=3)

    lesson: Mapped["Lesson"] = relationship(back_populates="checklist_items")


class Homework(Base):
    __tablename__ = "homeworks"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    lesson_id: Mapped[int] = mapped_column(ForeignKey("lessons.id"), unique=True)
    homework_text: Mapped[str] = mapped_column(Text, default="")
    due_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    lesson: Mapped["Lesson"] = relationship(back_populates="homework")
    submissions: Mapped[list["HomeworkSubmission"]] = relationship(
        back_populates="homework", cascade="all, delete-orphan"
    )


class HomeworkSubmission(Base):
    __tablename__ = "homework_submissions"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    homework_id: Mapped[int] = mapped_column(ForeignKey("homeworks.id", ondelete="CASCADE"), index=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("students.id", ondelete="CASCADE"), index=True)
    file_path: Mapped[str] = mapped_column(String(512))
    original_filename: Mapped[str] = mapped_column(String(255), default="")
    mime_type: Mapped[str] = mapped_column(String(100), default="")
    comment: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(20), default="submitted")
    tutor_comment: Mapped[str] = mapped_column(Text, default="")
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    ai_review_status: Mapped[str] = mapped_column(String(20), default="pending")
    ai_verdict: Mapped[str] = mapped_column(String(30), default="")
    ai_score: Mapped[int | None] = mapped_column(nullable=True)
    ai_feedback: Mapped[str] = mapped_column(Text, default="")
    ai_review_error: Mapped[str] = mapped_column(Text, default="")
    ai_reviewed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    submitted_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    homework: Mapped["Homework"] = relationship(back_populates="submissions")
    student: Mapped["Student"] = relationship()


class LessonPackage(Base):
    __tablename__ = "lesson_packages"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    tutor_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("students.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(255), default="")
    lessons_total: Mapped[int] = mapped_column(Integer)
    lessons_remaining: Mapped[int] = mapped_column(Integer)
    price_per_lesson: Mapped[float] = mapped_column(Float, default=0.0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    student: Mapped["Student"] = relationship(back_populates="packages")
    lessons: Mapped[list["Lesson"]] = relationship(back_populates="package")


class Board(Base):
    __tablename__ = "boards"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    title: Mapped[str] = mapped_column(String(255), default="Виртуальная доска")
    share_token: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    share_writable: Mapped[bool] = mapped_column(Boolean, default=True)
    state_json: Mapped[str] = mapped_column(
        Text,
        default='{"version":1,"strokes":[],"texts":[],"images":[]}',
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    owner: Mapped["User"] = relationship()
    snapshots: Mapped[list["BoardSnapshot"]] = relationship(
        back_populates="board", cascade="all, delete-orphan"
    )


class BoardSnapshot(Base):
    """Point-in-time board state for recovery and future event sourcing."""

    __tablename__ = "board_snapshots"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    board_id: Mapped[int] = mapped_column(ForeignKey("boards.id", ondelete="CASCADE"), index=True)
    state_json: Mapped[str] = mapped_column(Text, default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)

    board: Mapped["Board"] = relationship(back_populates="snapshots")


class NotificationLog(Base):
    __tablename__ = "notification_log"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    kind: Mapped[str] = mapped_column(String(40))
    ref_key: Mapped[str] = mapped_column(String(120), unique=True, index=True)
    sent_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class LessonSeries(Base):
    __tablename__ = "lesson_series"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    tutor_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("students.id", ondelete="CASCADE"), index=True)
    weekday: Mapped[int] = mapped_column(Integer)  # 0=Monday .. 6=Sunday (Python date.weekday)
    lesson_time: Mapped[str] = mapped_column(String(5), default="10:00")
    duration_minutes: Mapped[int] = mapped_column(Integer, default=60)
    payment_amount: Mapped[float] = mapped_column(Float, default=0.0)
    notes: Mapped[str] = mapped_column(Text, default="")
    starts_on: Mapped[date] = mapped_column(Date)
    until_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    weeks_ahead: Mapped[int] = mapped_column(Integer, default=8)
    last_generated_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    student: Mapped["Student"] = relationship()
    lessons: Mapped[list["Lesson"]] = relationship(back_populates="series")


class TrialBooking(Base):
    __tablename__ = "trial_bookings"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    tutor_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("students.id", ondelete="CASCADE"), index=True)
    preferred_date: Mapped[date] = mapped_column(Date)
    preferred_time: Mapped[str] = mapped_column(String(5), default="10:00")
    parent_message: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(20), default="new")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    tutor: Mapped["User"] = relationship(back_populates="trial_bookings")
    student: Mapped["Student"] = relationship(back_populates="trial_bookings")


class PaymentReceipt(Base):
    __tablename__ = "payment_receipts"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    tutor_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("students.id", ondelete="CASCADE"), index=True)
    amount: Mapped[float] = mapped_column(Float)
    status: Mapped[str] = mapped_column(String(20), default="pending", index=True)
    file_path: Mapped[str] = mapped_column(String(512), default="")
    original_filename: Mapped[str] = mapped_column(String(255), default="")
    mime_type: Mapped[str] = mapped_column(String(80), default="")
    parent_note: Mapped[str] = mapped_column(Text, default="")
    tutor_note: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    tutor: Mapped["User"] = relationship()
    student: Mapped["Student"] = relationship()


class LessonRescheduleRequest(Base):
    __tablename__ = "lesson_reschedule_requests"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    lesson_id: Mapped[int] = mapped_column(ForeignKey("lessons.id", ondelete="CASCADE"), index=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("students.id", ondelete="CASCADE"), index=True)
    tutor_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    message: Mapped[str] = mapped_column(Text, default="")
    preferred_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    preferred_time: Mapped[str] = mapped_column(String(5), default="")
    status: Mapped[str] = mapped_column(String(20), default="pending")  # pending|approved|rejected
    tutor_note: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    lesson: Mapped["Lesson"] = relationship()
    student: Mapped["Student"] = relationship()
    tutor: Mapped["User"] = relationship()


class StudentDailyChallenge(Base):
    """One short practice task per day when there is no lesson — keeps streak alive."""

    __tablename__ = "student_daily_challenges"
    __table_args__ = (
        UniqueConstraint("student_id", "challenge_date", name="uq_daily_challenge_student_date"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("students.id", ondelete="CASCADE"), index=True)
    challenge_date: Mapped[date] = mapped_column(Date, index=True)
    question: Mapped[str] = mapped_column(Text, default="")
    topic: Mapped[str] = mapped_column(String(255), default="")
    difficulty: Mapped[str] = mapped_column(String(20), default="easy")
    expected_hint: Mapped[str] = mapped_column(Text, default="")
    answer_text: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(20), default="open")
    ai_verdict: Mapped[str] = mapped_column(String(30), default="")
    ai_score: Mapped[int | None] = mapped_column(nullable=True)
    ai_feedback: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    answered_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    student: Mapped["Student"] = relationship(back_populates="daily_challenges")
