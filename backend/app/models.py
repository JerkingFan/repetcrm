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
    homework_prefs: Mapped[str] = mapped_column(Text, default="")
    notes: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    tutor: Mapped["User"] = relationship(back_populates="lessons")
    student: Mapped["Student"] = relationship(back_populates="lessons")
    board: Mapped["Board | None"] = relationship()
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
