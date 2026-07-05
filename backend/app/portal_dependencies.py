"""Student portal dependency."""

from __future__ import annotations

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.auth import decode_portal_token
from app.database import get_db
from app.models import Student
from app.portal_cookies import read_portal_token

optional_security = HTTPBearer(auto_error=False)


def _student_from_token(token: str | None, db: Session) -> Student | None:
    if not token:
        return None
    payload = decode_portal_token(token)
    if not payload or "sub" not in payload:
        return None
    return db.query(Student).filter(Student.id == int(payload["sub"])).first()


def get_current_student(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(optional_security),
    db: Session = Depends(get_db),
) -> Student:
    token = None
    if credentials and credentials.credentials:
        token = credentials.credentials
    if not token:
        token = read_portal_token(request)
    student = _student_from_token(token, db)
    if not student:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Portal session required")
    return student
