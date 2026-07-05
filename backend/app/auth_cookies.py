"""HttpOnly access-token cookie (refresh token lives on /auth)."""

from __future__ import annotations

from fastapi import Request, Response

from app.config import get_settings


def set_access_cookie(response: Response, access_token: str) -> None:
    cfg = get_settings()
    response.set_cookie(
        key=cfg.access_cookie_name,
        value=access_token,
        httponly=True,
        secure=cfg.cookie_secure,
        samesite="lax",
        max_age=cfg.access_token_expire_minutes * 60,
        path="/",
    )


def clear_access_cookie(response: Response) -> None:
    cfg = get_settings()
    response.delete_cookie(key=cfg.access_cookie_name, path="/")


def read_access_token(request: Request) -> str | None:
    cfg = get_settings()
    raw = request.cookies.get(cfg.access_cookie_name)
    if not raw or not str(raw).strip():
        return None
    return str(raw).strip()
