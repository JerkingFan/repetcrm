from datetime import datetime, date
from typing import Optional

from pydantic import BaseModel, EmailStr, Field, field_validator

from app.password_policy import validate_password_strength
from app.schemas.constraints import *  # noqa: F403

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
