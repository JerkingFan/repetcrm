from datetime import datetime, date
from typing import Optional

from pydantic import BaseModel, EmailStr, Field, field_validator

from app.password_policy import validate_password_strength
from app.schemas.constraints import *  # noqa: F403

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
    contact_telegram: str = ""
    contact_url: str = ""
    hide_balance_in_portal: bool = True
    smtp_configured: bool = False
    telegram_configured: bool = False


class NotificationSettingsUpdate(BaseModel):
    notify_email: Optional[bool] = None
    notify_telegram: Optional[bool] = None
    notify_lesson_tomorrow: Optional[bool] = None
    notify_unpaid: Optional[bool] = None
    notify_homework_ready: Optional[bool] = None
    telegram_chat_id: Optional[str] = None
    contact_telegram: Optional[str] = None
    contact_url: Optional[str] = None
    hide_balance_in_portal: Optional[bool] = None


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
