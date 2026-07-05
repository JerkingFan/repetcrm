"""Persistent portal link token per student."""

from __future__ import annotations

import secrets

from sqlalchemy.orm import Session

from app.models import Student


def ensure_portal_token(db: Session, student: Student) -> str:
    if student.portal_token:
        return student.portal_token
    token = secrets.token_urlsafe(32)
    student.portal_token = token
    db.flush()
    return token


def regenerate_portal_token(db: Session, student: Student) -> str:
    token = secrets.token_urlsafe(32)
    student.portal_token = token
    db.flush()
    return token


def student_by_portal_token(db: Session, raw_token: str) -> Student | None:
    if not raw_token or not raw_token.strip():
        return None
    return db.query(Student).filter(Student.portal_token == raw_token.strip()).first()


def ensure_parent_portal_token(db: Session, student: Student) -> str:
    if student.parent_portal_token:
        return student.parent_portal_token
    token = secrets.token_urlsafe(32)
    student.parent_portal_token = token
    db.flush()
    return token


def regenerate_parent_portal_token(db: Session, student: Student) -> str:
    token = secrets.token_urlsafe(32)
    student.parent_portal_token = token
    db.flush()
    return token


def student_by_parent_portal_token(db: Session, raw_token: str) -> Student | None:
    if not raw_token or not raw_token.strip():
        return None
    return db.query(Student).filter(Student.parent_portal_token == raw_token.strip()).first()


def student_by_any_portal_token(db: Session, raw_token: str) -> Student | None:
    student = student_by_portal_token(db, raw_token)
    if student:
        return student
    return student_by_parent_portal_token(db, raw_token)
