"""Refresh-token sessions stored in DB (hashed), cookie-friendly rotation."""

from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import AuthSession, User


def _hash_token(raw: str) -> str:
    return hashlib.sha256(raw.encode()).hexdigest()


def _new_refresh_token() -> str:
    return secrets.token_urlsafe(48)


def create_session(
    db: Session,
    user: User,
    *,
    ip: str = "",
    user_agent: str = "",
) -> tuple[str, AuthSession]:
    """Returns (raw_refresh_token, session row). Caller sets HttpOnly cookie."""
    cfg = get_settings()
    raw = _new_refresh_token()
    session = AuthSession(
        user_id=user.id,
        token_hash=_hash_token(raw),
        expires_at=datetime.utcnow() + timedelta(days=cfg.refresh_token_expire_days),
        last_ip=(ip or "")[:45],
        user_agent=(user_agent or "")[:512],
    )
    db.add(session)
    db.flush()
    return raw, session


def get_valid_session(db: Session, raw_token: str) -> AuthSession | None:
    if not raw_token.strip():
        return None
    token_hash = _hash_token(raw_token.strip())
    now = datetime.utcnow()
    session = (
        db.query(AuthSession)
        .filter(
            AuthSession.token_hash == token_hash,
            AuthSession.revoked_at.is_(None),
            AuthSession.expires_at > now,
        )
        .first()
    )
    return session


def revoke_session(db: Session, session: AuthSession) -> None:
    session.revoked_at = datetime.utcnow()


def rotate_session(
    db: Session,
    old_session: AuthSession,
    *,
    ip: str = "",
    user_agent: str = "",
) -> tuple[str, AuthSession]:
    """Revoke old session and issue a new refresh token (rotation)."""
    revoke_session(db, old_session)
    user = db.query(User).filter(User.id == old_session.user_id).first()
    if not user:
        raise ValueError("User not found")
    return create_session(db, user, ip=ip, user_agent=user_agent)
