from datetime import datetime, date

from sqlalchemy import String, Integer, Float, Boolean, ForeignKey, DateTime, Date, Text, Enum as SAEnum
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
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    students: Mapped[list["Student"]] = relationship(back_populates="tutor")
    lessons: Mapped[list["Lesson"]] = relationship(back_populates="tutor")
    auth_sessions: Mapped[list["AuthSession"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )


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
    notes: Mapped[str] = mapped_column(Text, default="")
    boundary_mode: Mapped[str] = mapped_column(String(20), default=StudentBoundaryMode.normal.value)
    boundary_reason: Mapped[str] = mapped_column(Text, default="")
    boundary_updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    tutor: Mapped["User"] = relationship(back_populates="students")
    lessons: Mapped[list["Lesson"]] = relationship(back_populates="student")


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
    is_conducted: Mapped[bool] = mapped_column(Boolean, default=False)
    status: Mapped[str] = mapped_column(String(20), default=LessonStatus.scheduled.value)
    late_minutes: Mapped[int] = mapped_column(Integer, default=0)
    rescheduled_from_lesson_id: Mapped[int | None] = mapped_column(
        ForeignKey("lessons.id"), nullable=True
    )
    status_changed_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    homework_prefs: Mapped[str] = mapped_column(Text, default="")
    notes: Mapped[str] = mapped_column(Text, default="")
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
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    lesson: Mapped["Lesson"] = relationship(back_populates="homework")


class Board(Base):
    __tablename__ = "boards"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    title: Mapped[str] = mapped_column(String(255), default="Виртуальная доска")
    share_token: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    state_json: Mapped[str] = mapped_column(
        Text,
        default='{"version":1,"strokes":[],"texts":[],"images":[]}',
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    owner: Mapped["User"] = relationship()
