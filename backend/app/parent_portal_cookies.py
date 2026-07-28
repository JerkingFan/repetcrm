"""HttpOnly parent portal session cookie."""

from __future__ import annotations

from fastapi import Request, Response

from app.config import get_settings

PARENT_PORTAL_COOKIE_NAME = "parent_session"


def set_parent_portal_cookie(response: Response, token: str) -> None:
    cfg = get_settings()
    response.set_cookie(
        key=PARENT_PORTAL_COOKIE_NAME,
        value=token,
        httponly=True,
        secure=cfg.cookie_secure,
        samesite="lax",
        max_age=cfg.portal_session_expire_days * 86400,
        path="/",
    )


def clear_parent_portal_cookie(response: Response) -> None:
    cfg = get_settings()
    response.delete_cookie(
        key=PARENT_PORTAL_COOKIE_NAME,
        path="/",
        secure=cfg.cookie_secure,
        samesite="lax",
    )


def read_parent_portal_token(request: Request) -> str | None:
    raw = request.cookies.get(PARENT_PORTAL_COOKIE_NAME)
    if not raw or not str(raw).strip():
        return None
    return str(raw).strip()
