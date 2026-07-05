from __future__ import annotations

from datetime import datetime

from sqlalchemy.orm import Session

from app.models import Lesson, LessonPackage, Student


def try_auto_pay_lesson(db: Session, lesson: Lesson) -> str | None:
    """Apply package credit or balance. Returns message if payment applied."""
    if lesson.is_paid:
        return None
    if not lesson.is_conducted and lesson.status not in ("completed",):
        return None

    amount = float(lesson.payment_amount or 0)
    student = db.query(Student).filter(Student.id == lesson.student_id).first()
    if not student:
        return None

    if lesson.package_id:
        return None

    package = (
        db.query(LessonPackage)
        .filter(
            LessonPackage.student_id == lesson.student_id,
            LessonPackage.tutor_id == lesson.tutor_id,
            LessonPackage.is_active.is_(True),
            LessonPackage.lessons_remaining > 0,
        )
        .order_by(LessonPackage.created_at.asc())
        .first()
    )
    if package:
        package.lessons_remaining -= 1
        if package.lessons_remaining <= 0:
            package.is_active = False
        lesson.is_paid = True
        lesson.package_id = package.id
        lesson.payment_source = "package"
        lesson.paid_at = datetime.utcnow()
        if amount <= 0:
            lesson.payment_amount = package.price_per_lesson
        db.flush()
        return f"Списано с абонемента «{package.name}» (осталось {package.lessons_remaining})"

    if amount > 0 and student.balance >= amount:
        student.balance = round(student.balance - amount, 2)
        lesson.is_paid = True
        lesson.payment_source = "balance"
        lesson.paid_at = datetime.utcnow()
        db.flush()
        return f"Списано с баланса ({amount} Br, осталось {student.balance} Br)"

    return None
