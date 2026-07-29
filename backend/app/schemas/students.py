from datetime import datetime, date
from typing import Optional

from pydantic import BaseModel, EmailStr, Field, field_validator

from app.password_policy import validate_password_strength
from app.schemas.constraints import *  # noqa: F403

class StudentCreate(BaseModel):
    name: str = Field(min_length=1, max_length=NAME_MAX)
    subject: str = Field(default="", max_length=SUBJECT_MAX)
    grade: str = Field(default="", max_length=GRADE_MAX)
    school: str = Field(default="", max_length=SCHOOL_MAX)
    contact: str = Field(default="", max_length=CONTACT_MAX)
    parent_contact: str = Field(default="", max_length=CONTACT_MAX)
    parent_name: str = Field(default="", max_length=NAME_MAX)
    parent_email: str = Field(default="", max_length=EMAIL_MAX)
    parent_phone: str = Field(default="", max_length=PHONE_MAX)
    parent_notify_email: bool = True
    notes: str = Field(default="", max_length=NOTES_MAX)


class StudentUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=NAME_MAX)
    subject: Optional[str] = Field(default=None, max_length=SUBJECT_MAX)
    grade: Optional[str] = Field(default=None, max_length=GRADE_MAX)
    school: Optional[str] = Field(default=None, max_length=SCHOOL_MAX)
    contact: Optional[str] = Field(default=None, max_length=CONTACT_MAX)
    parent_contact: Optional[str] = Field(default=None, max_length=CONTACT_MAX)
    parent_name: Optional[str] = Field(default=None, max_length=NAME_MAX)
    parent_email: Optional[str] = Field(default=None, max_length=EMAIL_MAX)
    parent_phone: Optional[str] = Field(default=None, max_length=PHONE_MAX)
    parent_notify_email: Optional[bool] = None
    notes: Optional[str] = Field(default=None, max_length=NOTES_MAX)


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
