"""HttpOnly portal session cookie for student cabinet."""

from __future__ import annotations

from fastapi import Request, Response

from app.config import get_settings

PORTAL_COOKIE_NAME = "portal_session"


def set_portal_cookie(response: Response, token: str) -> None:
    cfg = get_settings()
    response.set_cookie(
        key=PORTAL_COOKIE_NAME,
        value=token,
        httponly=True,
        secure=cfg.cookie_secure,
        samesite="lax",
        max_age=cfg.portal_session_expire_days * 86400,
        path="/",
    )


def clear_portal_cookie(response: Response) -> None:
    response.delete_cookie(key=PORTAL_COOKIE_NAME, path="/")


def read_portal_token(request: Request) -> str | None:
    raw = request.cookies.get(PORTAL_COOKIE_NAME)
    if not raw or not str(raw).strip():
        return None
    return str(raw).strip()
