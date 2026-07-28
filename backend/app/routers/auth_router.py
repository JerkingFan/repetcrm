import asyncio
import logging
import random

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.orm import Session

from app.auth import create_access_token, get_password_hash, verify_password
from app.auth_cookies import clear_access_cookie, set_access_cookie
from app.config import get_settings
from app.database import get_db
from app.dependencies import get_current_user
from app.http_utils import get_client_ip
from app.models import User
from app.schemas import (
    UserRegister,
    UserLogin,
    Token,
    UserOut,
    OnboardingComplete,
    OnboardingUpdate,
    ForgotPasswordIn,
    ResetPasswordIn,
    ChangePasswordIn,
    NotificationSettingsOut,
    NotificationSettingsUpdate,
    MessageOut,
    PaymentRequisitesOut,
    PaymentRequisitesUpdate,
)
from app.services.password_reset import consume_reset_token, create_reset_token, send_reset_email
from app.services.mailer import smtp_configured
from app.services.auth_rate_limit import (
    email_fingerprint,
    get_login_limiter,
    get_register_limiter,
    redact_email,
)
from app.db_migrate import repair_legacy_schema
from app.services.auth_sessions import (
    create_session,
    get_valid_session,
    revoke_session,
    rotate_session,
)
from app.services.dashboard_cache import invalidate_dashboard
from app.utils import to_json_list, from_json_list

router = APIRouter(prefix="/auth", tags=["auth"])
logger = logging.getLogger("app.auth")


def user_to_out(user: User) -> UserOut:
    return UserOut(
        id=user.id,
        email=user.email,
        name=user.name,
        onboarding_completed=user.onboarding_completed,
        subjects=from_json_list(user.subjects),
        grade_levels=from_json_list(user.grade_levels),
        teaching_format=user.teaching_format or "",
    )


def _login_rate_key(ip: str, email: str) -> str:
    return f"{ip}:{email.strip().lower()}"


def _client_meta(request: Request) -> tuple[str, str]:
    ip = get_client_ip(request)
    ua = (request.headers.get("user-agent") or "")[:512]
    return ip, ua


def _set_refresh_cookie(response: Response, raw_token: str) -> None:
    cfg = get_settings()
    # path="/" — cookie уходит и на /auth/*, и на /api/auth/* (nginx proxy)
    response.set_cookie(
        key=cfg.refresh_cookie_name,
        value=raw_token,
        httponly=True,
        secure=cfg.cookie_secure,
        samesite="lax",
        max_age=cfg.refresh_token_expire_days * 86400,
        path="/",
    )


def _clear_refresh_cookie(response: Response) -> None:
    cfg = get_settings()
    response.delete_cookie(key=cfg.refresh_cookie_name, path="/")
    # старый path=/auth (до фикса nginx /api) — подчистить
    response.delete_cookie(key=cfg.refresh_cookie_name, path="/auth")
    response.delete_cookie(key=cfg.refresh_cookie_name, path="/api/auth")


def _issue_tokens(
    db: Session,
    user: User,
    response: Response,
    request: Request,
) -> Token:
    ip, ua = _client_meta(request)
    raw_refresh, _session = create_session(db, user, ip=ip, user_agent=ua)
    db.commit()
    access = create_access_token(user.id)
    _set_refresh_cookie(response, raw_refresh)
    set_access_cookie(response, access)
    return Token(access_token="", token_type="cookie")


@router.post("/register", response_model=Token)
def register(
    data: UserRegister,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
):
    cfg = get_settings()
    ip = get_client_ip(request)
    register_limiter = get_register_limiter(cfg.auth_register_max_per_ip, cfg.auth_register_window_sec)

    if register_limiter.is_blocked(ip):
        retry = register_limiter.retry_after_sec(ip)
        logger.warning("auth_register_rate_limited ip=%s retry_after=%s", ip, retry)
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many registration attempts. Try again later.",
            headers={"Retry-After": str(retry)},
        )

    if db.query(User).filter(User.email == data.email).first():
        register_limiter.record(ip)
        raise HTTPException(status_code=400, detail="Email already registered")

    user = User(
        email=data.email,
        hashed_password=get_password_hash(data.password),
        name=data.name or data.email.split("@")[0],
        onboarding_completed=False,
    )
    db.add(user)
    db.flush()
    register_limiter.record(ip)
    logger.info("auth_register_ok user_id=%s ip=%s", user.id, ip)
    invalidate_dashboard(user.id)
    return _issue_tokens(db, user, response, request)


@router.post("/login", response_model=Token)
async def login(data: UserLogin, request: Request, response: Response, db: Session = Depends(get_db)):
    repair_legacy_schema()
    cfg = get_settings()
    ip = get_client_ip(request)
    rate_key = _login_rate_key(ip, data.email)
    login_limiter = get_login_limiter(cfg.auth_login_max_failures, cfg.auth_login_window_sec)

    if login_limiter.is_blocked(rate_key):
        retry = login_limiter.retry_after_sec(rate_key)
        logger.warning(
            "auth_login_rate_limited ip=%s email=%s fp=%s retry_after=%s",
            ip,
            redact_email(data.email),
            email_fingerprint(data.email),
            retry,
        )
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many login attempts. Try again in a minute.",
            headers={"Retry-After": str(retry)},
        )

    user = db.query(User).filter(User.email == data.email).first()
    if not user or not verify_password(data.password, user.hashed_password):
        failures = login_limiter.record(rate_key)
        delay = cfg.auth_login_fail_delay_sec
        if delay > 0:
            await asyncio.sleep(delay + random.uniform(0, min(0.3, delay)))
        logger.warning(
            "auth_login_failed ip=%s email=%s fp=%s failures_in_window=%s",
            ip,
            redact_email(data.email),
            email_fingerprint(data.email),
            failures,
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    login_limiter.clear(rate_key)
    logger.info("auth_login_ok user_id=%s ip=%s", user.id, ip)
    return _issue_tokens(db, user, response, request)


@router.post("/refresh", response_model=Token)
def refresh_token(request: Request, response: Response, db: Session = Depends(get_db)):
    cfg = get_settings()
    raw = request.cookies.get(cfg.refresh_cookie_name)
    if not raw:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing refresh token")

    session = get_valid_session(db, raw)
    if not session:
        _clear_refresh_cookie(response)
        clear_access_cookie(response)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")

    ip, ua = _client_meta(request)
    try:
        new_raw, _new_session = rotate_session(db, session, ip=ip, user_agent=ua)
    except ValueError:
        _clear_refresh_cookie(response)
        clear_access_cookie(response)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")

    db.commit()
    access = create_access_token(session.user_id)
    _set_refresh_cookie(response, new_raw)
    set_access_cookie(response, access)
    return Token(access_token="", token_type="cookie")


@router.post("/logout", status_code=204)
def logout(request: Request, response: Response, db: Session = Depends(get_db)):
    cfg = get_settings()
    raw = request.cookies.get(cfg.refresh_cookie_name)
    if raw:
        session = get_valid_session(db, raw)
        if session:
            revoke_session(db, session)
            db.commit()
    _clear_refresh_cookie(response)
    clear_access_cookie(response)


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)):
    return user_to_out(user)


@router.post("/onboarding", response_model=UserOut)
def complete_onboarding(
    data: OnboardingComplete,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    user.subjects = to_json_list(data.subjects)
    user.grade_levels = to_json_list(data.grade_levels)
    user.teaching_format = data.teaching_format or ""
    user.onboarding_completed = True
    db.commit()
    db.refresh(user)
    return user_to_out(user)


@router.put("/profile", response_model=UserOut)
def update_profile(
    data: OnboardingUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if data.subjects is not None:
        user.subjects = to_json_list(data.subjects)
    if data.grade_levels is not None:
        user.grade_levels = to_json_list(data.grade_levels)
    if data.teaching_format is not None:
        user.teaching_format = data.teaching_format
    db.commit()
    db.refresh(user)
    return user_to_out(user)


@router.post("/forgot-password", response_model=MessageOut)
def forgot_password(data: ForgotPasswordIn, request: Request, db: Session = Depends(get_db)):
    cfg = get_settings()
    ip = get_client_ip(request)
    limiter = get_register_limiter(5, 3600)
    if limiter.is_blocked(f"forgot:{ip}"):
        raise HTTPException(status_code=429, detail="Too many requests")
    limiter.record(f"forgot:{ip}")

    user = db.query(User).filter(User.email == data.email).first()
    if user:
        raw = create_reset_token(db, user)
        db.commit()
        send_reset_email(user, raw)
    return MessageOut(message="If the email exists, a reset link has been sent.")


@router.post("/reset-password", response_model=MessageOut)
def reset_password(data: ResetPasswordIn, db: Session = Depends(get_db)):
    user = consume_reset_token(db, data.token)
    if not user:
        raise HTTPException(status_code=400, detail="Invalid or expired reset token")
    user.hashed_password = get_password_hash(data.password)
    db.commit()
    return MessageOut(message="Password updated. You can log in now.")


@router.post("/change-password", response_model=MessageOut)
def change_password(
    data: ChangePasswordIn,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not verify_password(data.current_password, user.hashed_password):
        raise HTTPException(status_code=400, detail="Current password is incorrect")
    user.hashed_password = get_password_hash(data.new_password)
    db.commit()
    return MessageOut(message="Password changed.")


@router.get("/notification-settings", response_model=NotificationSettingsOut)
def get_notification_settings(user: User = Depends(get_current_user)):
    cfg = get_settings()
    return NotificationSettingsOut(
        notify_email=user.notify_email,
        notify_telegram=user.notify_telegram,
        notify_lesson_tomorrow=user.notify_lesson_tomorrow,
        notify_unpaid=user.notify_unpaid,
        notify_homework_ready=user.notify_homework_ready,
        telegram_chat_id=user.telegram_chat_id or "",
        contact_telegram=getattr(user, "contact_telegram", "") or "",
        contact_url=getattr(user, "contact_url", "") or "",
        hide_balance_in_portal=bool(getattr(user, "hide_balance_in_portal", True)),
        smtp_configured=smtp_configured(),
        telegram_configured=bool(cfg.telegram_bot_token.strip()),
    )


@router.put("/notification-settings", response_model=NotificationSettingsOut)
def update_notification_settings(
    data: NotificationSettingsUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if data.notify_email is not None:
        user.notify_email = data.notify_email
    if data.notify_telegram is not None:
        user.notify_telegram = data.notify_telegram
    if data.notify_lesson_tomorrow is not None:
        user.notify_lesson_tomorrow = data.notify_lesson_tomorrow
    if data.notify_unpaid is not None:
        user.notify_unpaid = data.notify_unpaid
    if data.notify_homework_ready is not None:
        user.notify_homework_ready = data.notify_homework_ready
    if data.telegram_chat_id is not None:
        user.telegram_chat_id = data.telegram_chat_id.strip()
    if data.contact_telegram is not None:
        user.contact_telegram = data.contact_telegram.strip().lstrip("@")
    if data.contact_url is not None:
        user.contact_url = data.contact_url.strip()
    if data.hide_balance_in_portal is not None:
        user.hide_balance_in_portal = data.hide_balance_in_portal
    db.commit()
    db.refresh(user)
    cfg = get_settings()
    return NotificationSettingsOut(
        notify_email=user.notify_email,
        notify_telegram=user.notify_telegram,
        notify_lesson_tomorrow=user.notify_lesson_tomorrow,
        notify_unpaid=user.notify_unpaid,
        notify_homework_ready=user.notify_homework_ready,
        telegram_chat_id=user.telegram_chat_id or "",
        contact_telegram=getattr(user, "contact_telegram", "") or "",
        contact_url=getattr(user, "contact_url", "") or "",
        hide_balance_in_portal=bool(getattr(user, "hide_balance_in_portal", True)),
        smtp_configured=smtp_configured(),
        telegram_configured=bool(cfg.telegram_bot_token.strip()),
    )


@router.get("/payment-requisites", response_model=PaymentRequisitesOut)
def get_payment_requisites(user: User = Depends(get_current_user)):
    return PaymentRequisitesOut(payment_details=user.payment_details or "")


@router.put("/payment-requisites", response_model=PaymentRequisitesOut)
def update_payment_requisites(
    data: PaymentRequisitesUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    user.payment_details = (data.payment_details or "").strip()
    db.commit()
    db.refresh(user)
    return PaymentRequisitesOut(payment_details=user.payment_details)
