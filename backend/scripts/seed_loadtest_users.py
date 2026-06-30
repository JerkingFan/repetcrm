#!/usr/bin/env python3
"""
Seed tutors + students + lessons for load testing (idempotent).

Usage (inside backend container or venv):
  python scripts/seed_loadtest_users.py --count 50 --students 10 --lessons 20
  python scripts/seed_loadtest_users.py --cleanup
"""

from __future__ import annotations

import argparse
import json
import secrets
import sys
from datetime import date, timedelta
from pathlib import Path

# Allow running as: python backend/scripts/seed_loadtest_users.py from repo root
_BACKEND = Path(__file__).resolve().parent.parent
if str(_BACKEND) not in sys.path:
    sys.path.insert(0, str(_BACKEND))

from sqlalchemy import or_

from app.auth import get_password_hash  # noqa: E402
from app.database import SessionLocal, init_db  # noqa: E402
from app.models import User, Student, Lesson  # noqa: E402


LOADTEST_EMAIL_DOMAIN = "loadtest.example.com"
DEFAULT_PASSWORD = "LoadTest123!"


def _email(i: int) -> str:
    return f"tutor-{i:03d}@{LOADTEST_EMAIL_DOMAIN}"


def seed(
    *,
    count: int,
    students_per_tutor: int,
    lessons_per_student: int,
    password: str,
    output: Path,
) -> dict:
    init_db()
    db = SessionLocal()
    created_users = 0
    users_out: list[dict] = []

    try:
        today = date.today()
        month_start = today.replace(day=1)

        for i in range(1, count + 1):
            email = _email(i)
            user = db.query(User).filter(User.email == email).first()
            if not user:
                user = User(
                    email=email,
                    hashed_password=get_password_hash(password),
                    name=f"LoadTest Tutor {i:03d}",
                    onboarding_completed=True,
                    subjects='["math"]',
                    grade_levels='["9","10"]',
                    teaching_format="online",
                )
                db.add(user)
                db.flush()
                created_users += 1

            existing_students = (
                db.query(Student).filter(Student.tutor_id == user.id).count()
            )
            to_create = max(0, students_per_tutor - existing_students)
            students: list[Student] = list(
                db.query(Student).filter(Student.tutor_id == user.id).all()
            )

            for s_idx in range(to_create):
                st = Student(
                    tutor_id=user.id,
                    name=f"Student {s_idx + 1} (T{i:03d})",
                    subject="math",
                    grade="9",
                )
                db.add(st)
                db.flush()
                students.append(st)

            for st in students:
                existing_lessons = (
                    db.query(Lesson).filter(Lesson.student_id == st.id).count()
                )
                need = max(0, lessons_per_student - existing_lessons)
                for l_idx in range(need):
                    lesson_date = month_start + timedelta(days=(l_idx % 28))
                    db.add(
                        Lesson(
                            tutor_id=user.id,
                            student_id=st.id,
                            lesson_date=lesson_date,
                            lesson_time="10:00",
                            duration_minutes=60,
                            payment_amount=50.0,
                            is_paid=l_idx % 3 == 0,
                            is_conducted=lesson_date < today,
                            status="completed" if lesson_date < today else "scheduled",
                        )
                    )

            users_out.append({"email": email, "password": password, "name": user.name})

        db.commit()
    finally:
        db.close()

    output.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "domain": LOADTEST_EMAIL_DOMAIN,
        "count": len(users_out),
        "password": password,
        "users": users_out,
    }
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    return {
        "users_total": len(users_out),
        "users_created": created_users,
        "output": str(output),
    }


def cleanup(*, count: int) -> int:
    init_db()
    db = SessionLocal()
    deleted = 0
    try:
        users = (
            db.query(User)
            .filter(
                or_(
                    User.email.like(f"%@{LOADTEST_EMAIL_DOMAIN}"),
                    User.email.like("%@loadtest.local"),
                )
            )
            .all()
        )
        user_ids = [u.id for u in users]
        if user_ids:
            # User.students has no ORM cascade — delete children explicitly
            db.query(Lesson).filter(Lesson.tutor_id.in_(user_ids)).delete(
                synchronize_session=False
            )
            db.query(Student).filter(Student.tutor_id.in_(user_ids)).delete(
                synchronize_session=False
            )
            for user in users:
                db.delete(user)
                deleted += 1
        db.commit()
    finally:
        db.close()
    return deleted


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed load-test data for RepetCRM")
    parser.add_argument("--count", type=int, default=50, help="Number of tutor accounts")
    parser.add_argument("--students", type=int, default=10, help="Students per tutor")
    parser.add_argument("--lessons", type=int, default=20, help="Lessons per student")
    parser.add_argument("--password", type=str, default=DEFAULT_PASSWORD)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("/tmp/repetcrm_loadtest_users.json"),
    )
    parser.add_argument("--cleanup", action="store_true", help="Remove loadtest users")
    args = parser.parse_args()

    if args.cleanup:
        n = cleanup(count=args.count)
        print(json.dumps({"deleted_users": n}, ensure_ascii=False))
        return

    result = seed(
        count=args.count,
        students_per_tutor=args.students,
        lessons_per_student=args.lessons,
        password=args.password,
        output=args.output,
    )
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
