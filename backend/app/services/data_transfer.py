"""CSV export and import for students and lessons."""

from __future__ import annotations

import csv
import io
import secrets
from typing import BinaryIO

from sqlalchemy.orm import Session

from app.models import Board, Homework, Lesson, LessonStatus, Student
from app.schemas import ImportResultOut
from app.services.parent_contact import sync_parent_contact, parse_legacy_parent_contact

STUDENT_HEADERS = [
    "name",
    "subject",
    "grade",
    "school",
    "contact",
    "parent_name",
    "parent_email",
    "parent_phone",
    "parent_contact",
    "notes",
]

LESSON_HEADERS = [
    "student_name",
    "lesson_date",
    "lesson_time",
    "duration_minutes",
    "payment_amount",
    "is_paid",
    "is_conducted",
    "status",
    "notes",
]


def _bool_cell(value: str) -> bool:
    return value.strip().lower() in ("1", "true", "yes", "да", "y")


def export_students_csv(db: Session, tutor_id: int) -> bytes:
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(STUDENT_HEADERS)
    for s in db.query(Student).filter(Student.tutor_id == tutor_id).order_by(Student.name).all():
        writer.writerow(
            [
                s.name,
                s.subject or "",
                s.grade or "",
                s.school or "",
                s.contact or "",
                s.parent_name or "",
                s.parent_email or "",
                s.parent_phone or "",
                s.parent_contact or "",
                s.notes or "",
            ]
        )
    return ("\ufeff" + buf.getvalue()).encode("utf-8")


def export_lessons_csv(
    db: Session,
    tutor_id: int,
    *,
    from_date: date | None = None,
    to_date: date | None = None,
) -> bytes:
    q = (
        db.query(Lesson, Student.name)
        .join(Student, Lesson.student_id == Student.id)
        .filter(Lesson.tutor_id == tutor_id)
    )
    if from_date:
        q = q.filter(Lesson.lesson_date >= from_date)
    if to_date:
        q = q.filter(Lesson.lesson_date <= to_date)
    rows = q.order_by(Lesson.lesson_date.desc(), Lesson.lesson_time.desc()).all()

    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(LESSON_HEADERS)
    for lesson, student_name in rows:
        writer.writerow(
            [
                student_name,
                lesson.lesson_date.isoformat(),
                lesson.lesson_time or "10:00",
                lesson.duration_minutes,
                lesson.payment_amount,
                "1" if lesson.is_paid else "0",
                "1" if lesson.is_conducted else "0",
                lesson.status or LessonStatus.scheduled.value,
                lesson.notes or "",
            ]
        )
    return ("\ufeff" + buf.getvalue()).encode("utf-8")


def _read_csv_rows(file: BinaryIO) -> tuple[list[str], list[dict[str, str]]]:
    raw = file.read()
    if raw.startswith(b"\xef\xbb\xbf"):
        raw = raw[3:]
    text = raw.decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(text))
    if not reader.fieldnames:
        return [], []
    headers = [h.strip() for h in reader.fieldnames if h]
    rows = [{k.strip(): (v or "").strip() for k, v in row.items() if k} for row in reader]
    return headers, rows


def import_students_csv(db: Session, tutor_id: int, file: BinaryIO) -> ImportResultOut:
    headers, rows = _read_csv_rows(file)
    if not rows:
        return ImportResultOut(created=0, updated=0, skipped=0, errors=["Empty file"])

    created = updated = skipped = 0
    errors: list[str] = []

    for i, row in enumerate(rows, start=2):
        name = row.get("name", "").strip()
        if not name:
            skipped += 1
            continue
        existing = (
            db.query(Student)
            .filter(Student.tutor_id == tutor_id, Student.name == name)
            .first()
        )
        payload = {
            "subject": row.get("subject", ""),
            "grade": row.get("grade", ""),
            "school": row.get("school", ""),
            "contact": row.get("contact", ""),
            "parent_name": row.get("parent_name", ""),
            "parent_email": row.get("parent_email", ""),
            "parent_phone": row.get("parent_phone", ""),
            "parent_contact": row.get("parent_contact", ""),
            "notes": row.get("notes", ""),
        }
        if not payload["parent_email"] and not payload["parent_phone"] and payload["parent_contact"]:
            email, phone = parse_legacy_parent_contact(payload["parent_contact"])
            payload["parent_email"] = email
            payload["parent_phone"] = phone
        try:
            if existing:
                for k, v in payload.items():
                    setattr(existing, k, v)
                sync_parent_contact(existing)
                updated += 1
            else:
                student = Student(tutor_id=tutor_id, name=name, **payload)
                sync_parent_contact(student)
                db.add(student)
                created += 1
        except Exception as exc:
            errors.append(f"Row {i}: {exc}")

    db.commit()
    return ImportResultOut(created=created, updated=updated, skipped=skipped, errors=errors[:20])


def import_lessons_csv(db: Session, tutor_id: int, file: BinaryIO) -> ImportResultOut:
    headers, rows = _read_csv_rows(file)
    if not rows:
        return ImportResultOut(created=0, updated=0, skipped=0, errors=["Empty file"])

    students_by_name = {
        s.name: s
        for s in db.query(Student).filter(Student.tutor_id == tutor_id).all()
    }

    created = updated = skipped = 0
    errors: list[str] = []

    for i, row in enumerate(rows, start=2):
        student_name = row.get("student_name", "").strip()
        date_raw = row.get("lesson_date", "").strip()
        if not student_name or not date_raw:
            skipped += 1
            continue
        student = students_by_name.get(student_name)
        if not student:
            student = Student(tutor_id=tutor_id, name=student_name, subject="", grade="")
            db.add(student)
            db.flush()
            students_by_name[student_name] = student

        try:
            lesson_date = date.fromisoformat(date_raw[:10])
        except ValueError:
            errors.append(f"Row {i}: invalid date {date_raw!r}")
            skipped += 1
            continue

        lesson_time = row.get("lesson_time", "10:00").strip() or "10:00"
        try:
            duration = int(row.get("duration_minutes", "60") or 60)
            payment = float(row.get("payment_amount", "0") or 0)
        except ValueError:
            errors.append(f"Row {i}: invalid number")
            skipped += 1
            continue

        status = (row.get("status") or LessonStatus.scheduled.value).strip().lower()
        if status not in {s.value for s in LessonStatus}:
            status = LessonStatus.scheduled.value

        existing = (
            db.query(Lesson)
            .filter(
                Lesson.tutor_id == tutor_id,
                Lesson.student_id == student.id,
                Lesson.lesson_date == lesson_date,
                Lesson.lesson_time == lesson_time,
            )
            .first()
        )
        fields = {
            "duration_minutes": duration,
            "payment_amount": payment,
            "is_paid": _bool_cell(row.get("is_paid", "0")),
            "is_conducted": _bool_cell(row.get("is_conducted", "0")),
            "status": status,
            "notes": row.get("notes", ""),
        }
        try:
            if existing:
                for k, v in fields.items():
                    setattr(existing, k, v)
                updated += 1
            else:
                board = Board(
                    owner_id=tutor_id,
                    title=f"Доска: {student.name}",
                    share_token=secrets.token_urlsafe(24),
                    share_writable=False,
                )
                db.add(board)
                db.flush()
                db.add(
                    Lesson(
                        tutor_id=tutor_id,
                        student_id=student.id,
                        board_id=board.id,
                        lesson_date=lesson_date,
                        lesson_time=lesson_time,
                        **fields,
                    )
                )
                created += 1
        except Exception as exc:
            errors.append(f"Row {i}: {exc}")

    db.commit()
    return ImportResultOut(created=created, updated=updated, skipped=skipped, errors=errors[:20])
