"""Email notifications for parents (payers)."""

from __future__ import annotations

import logging

from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import Lesson, LessonPackage, PaymentIntent, Student, User, Homework, HomeworkSubmission
from app.services.mailer import send_email
from app.services.notifications import _already_sent, _mark_sent
from app.services.homework_submission_review import status_label
from app.services.portal_token import ensure_parent_portal_token

logger = logging.getLogger(__name__)


def parent_portal_url(db: Session, student: Student) -> str:
    cfg = get_settings()
    base = cfg.public_site_url
    token = ensure_parent_portal_token(db, student)
    return f"{base}/parent?token={token}"


def _parent_recipient(student: Student) -> str | None:
    if not student.parent_notify_email:
        return None
    email = (student.parent_email or "").strip()
    if not email or "@" not in email:
        return None
    return email


def notify_parent(
    db: Session,
    student: Student,
    tutor: User,
    *,
    kind: str,
    ref_key: str,
    subject: str,
    body: str,
) -> bool:
    if _already_sent(db, ref_key):
        return False
    to = _parent_recipient(student)
    if not to:
        return False
    if not send_email(to=to, subject=subject, body=body):
        return False
    _mark_sent(db, tutor.id, kind, ref_key)
    return True


def lesson_price_hint(db: Session, student: Student, tutor_id: int) -> float:
    package = (
        db.query(LessonPackage)
        .filter(
            LessonPackage.student_id == student.id,
            LessonPackage.tutor_id == tutor_id,
            LessonPackage.is_active.is_(True),
            LessonPackage.price_per_lesson > 0,
        )
        .order_by(LessonPackage.created_at.desc())
        .first()
    )
    if package:
        return float(package.price_per_lesson)
    last_paid = (
        db.query(Lesson)
        .filter(
            Lesson.student_id == student.id,
            Lesson.tutor_id == tutor_id,
            Lesson.payment_amount > 0,
        )
        .order_by(Lesson.lesson_date.desc(), Lesson.id.desc())
        .first()
    )
    if last_paid:
        return float(last_paid.payment_amount)
    return 0.0


def notify_parent_lesson_tomorrow(
    db: Session,
    *,
    lesson: Lesson,
    student: Student,
    tutor: User,
    lesson_date_iso: str,
) -> bool:
    portal = parent_portal_url(db, student)
    tutor_name = (tutor.name or "репетитор").strip()
    subject = f"Завтра занятие: {student.name}"
    body = (
        f"Здравствуйте{', ' + student.parent_name if student.parent_name else ''}!\n\n"
        f"Напоминаем: завтра ({lesson_date_iso}) у {student.name} занятие "
        f"с {tutor_name} в {lesson.lesson_time} ({lesson.duration_minutes} мин).\n\n"
        f"Расписание и оплата: {portal}"
    )
    ref_key = f"parent:lesson_tomorrow:{lesson.id}:{lesson_date_iso}"
    return notify_parent(
        db,
        student,
        tutor,
        kind="parent_lesson_tomorrow",
        ref_key=ref_key,
        subject=subject,
        body=body,
    )


def notify_parent_low_balance(
    db: Session,
    *,
    student: Student,
    tutor: User,
    lesson_price: float,
    day_iso: str,
) -> bool:
    portal = parent_portal_url(db, student)
    balance = float(student.balance or 0)
    subject = f"Пополните баланс занятий: {student.name}"
    body = (
        f"Здравствуйте{', ' + student.parent_name if student.parent_name else ''}!\n\n"
        f"На балансе {student.name} осталось {balance:.2f} Br — этого может не хватить "
        f"на следующее занятие (≈ {lesson_price:.2f} Br).\n\n"
        f"Пополнить баланс: {portal}"
    )
    ref_key = f"parent:low_balance:{student.id}:{day_iso}"
    return notify_parent(
        db,
        student,
        tutor,
        kind="parent_low_balance",
        ref_key=ref_key,
        subject=subject,
        body=body,
    )


def notify_parent_payment_received(
    db: Session,
    *,
    student: Student,
    tutor: User,
    intent: PaymentIntent,
) -> bool:
    portal = parent_portal_url(db, student)
    balance = float(student.balance or 0)
    subject = f"Оплата получена: {student.name}"
    body = (
        f"Здравствуйте{', ' + student.parent_name if student.parent_name else ''}!\n\n"
        f"Зачислено {intent.amount:.2f} Br за занятия {student.name}. "
        f"Текущий баланс: {balance:.2f} Br.\n\n"
        f"Кабинет родителя: {portal}"
    )
    ref_key = f"parent:payment:{intent.id}"
    return notify_parent(
        db,
        student,
        tutor,
        kind="parent_payment_received",
        ref_key=ref_key,
        subject=subject,
        body=body,
    )


def notify_parent_homework_reviewed(
    db: Session,
    *,
    student: Student,
    tutor: User,
    homework: Homework,
    submission: HomeworkSubmission,
) -> bool:
    from app.models import Lesson

    lesson = db.query(Lesson).filter(Lesson.id == homework.lesson_id).first()
    lesson_date = lesson.lesson_date.isoformat() if lesson else "—"
    label = status_label(submission.status)
    portal = parent_portal_url(db, student)
    subject = f"ДЗ {student.name}: {label}"
    body = (
        f"Здравствуйте{', ' + student.parent_name if student.parent_name else ''}!\n\n"
        f"Домашнее задание от {lesson_date} — {label}."
    )
    if submission.tutor_comment:
        body += f"\n\nКомментарий репетитора: {submission.tutor_comment}"
    body += f"\n\nПодробности: {portal}"
    ref_key = f"parent:hw_review:{submission.id}:{submission.status}"
    return notify_parent(
        db,
        student,
        tutor,
        kind="parent_homework_reviewed",
        ref_key=ref_key,
        subject=subject,
        body=body,
    )


def send_parent_monthly_report_email(
    db: Session,
    *,
    student: Student,
    tutor: User,
    report,
    pdf_bytes: bytes,
) -> bool:
    to = _parent_recipient(student)
    if not to:
        return False
    month_label = report.month_label
    subject = f"Отчёт за {month_label}: {student.name}"
    body = (
        f"Здравствуйте{', ' + student.parent_name if student.parent_name else ''}!\n\n"
        f"Во вложении отчёт о занятиях {student.name} за {month_label}.\n\n"
        f"Проведено уроков: {report.lessons_conducted} из {report.lessons_total}.\n"
        f"Поступило оплат: {report.payments_total:.2f} Br.\n"
        f"Баланс: {report.balance:.2f} Br.\n\n"
        f"Кабинет родителя: {parent_portal_url(db, student)}"
    )
    ref_key = f"parent:report:{student.id}:{report.month}"
    if _already_sent(db, ref_key):
        return False
    from app.services.mailer import send_email_with_attachment

    filename = f"otchet-{student.name.replace(' ', '_')}-{report.month}.pdf"
    if not send_email_with_attachment(
        to=to,
        subject=subject,
        body=body,
        attachment_filename=filename,
        attachment_bytes=pdf_bytes,
    ):
        return False
    _mark_sent(db, tutor.id, "parent_monthly_report", ref_key)
    return True
