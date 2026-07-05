from datetime import datetime, timedelta, timezone

import bcrypt
from jose import JWTError, jwt

from app.config import settings


def verify_password(plain: str, hashed: str) -> bool:
    if not plain or not hashed:
        return False
    try:
        return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))
    except (ValueError, TypeError):
        return False


def get_password_hash(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def create_access_token(user_id: int) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.access_token_expire_minutes)
    payload = {"sub": str(user_id), "exp": expire, "type": "access"}
    return jwt.encode(payload, settings.secret_key, algorithm=settings.algorithm)


def create_portal_session_token(student_id: int) -> str:
    expire = datetime.now(timezone.utc) + timedelta(days=settings.portal_session_expire_days)
    payload = {"sub": str(student_id), "exp": expire, "type": "portal"}
    return jwt.encode(payload, settings.secret_key, algorithm=settings.algorithm)


def create_parent_portal_session_token(student_id: int) -> str:
    expire = datetime.now(timezone.utc) + timedelta(days=settings.portal_session_expire_days)
    payload = {"sub": str(student_id), "exp": expire, "type": "parent_portal"}
    return jwt.encode(payload, settings.secret_key, algorithm=settings.algorithm)


def decode_token(token: str) -> dict | None:
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
        if payload.get("type") and payload.get("type") != "access":
            return None
        return payload
    except JWTError:
        return None


def decode_portal_token(token: str) -> dict | None:
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
        if payload.get("type") != "portal":
            return None
        return payload
    except JWTError:
        return None


def decode_parent_portal_token(token: str) -> dict | None:
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
        if payload.get("type") != "parent_portal":
            return None
        return payload
    except JWTError:
        return None
