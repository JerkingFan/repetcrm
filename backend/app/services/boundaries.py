from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta

from sqlalchemy import and_, case, func
from sqlalchemy.orm import Session

from app.models import Lesson, Student, LessonStatus, StudentBoundaryMode

MODE_SEVERITY: dict[StudentBoundaryMode, int] = {
    StudentBoundaryMode.normal: 0,
    StudentBoundaryMode.yellow: 1,
    StudentBoundaryMode.orange: 2,
    StudentBoundaryMode.red: 3,
}

BOUNDARY_RULES: dict[StudentBoundaryMode, dict[str, str]] = {
    StudentBoundaryMode.normal: {
        "reschedule_notice": "по договорённости",
        "payment": "как обычно",
        "slots": "как обычно",
    },
    StudentBoundaryMode.yellow: {
        "reschedule_notice": "не позже чем за 24 часа",
        "payment": "как обычно",
        "slots": "как обычно",
    },
    StudentBoundaryMode.orange: {
        "reschedule_notice": "не позже чем за 24 часа",
        "payment": "предоплата 100% не позже чем за 24 часа до урока",
        "slots": "как обычно",
    },
    StudentBoundaryMode.red: {
        "reschedule_notice": "не позже чем за 48 часов",
        "payment": "предоплата 100% до подтверждения слота",
        "slots": "только в свободные окна в расписании",
    },
}


@dataclass(frozen=True)
class BoundaryDecision:
    mode: StudentBoundaryMode
    reason: str
    signals: dict[str, int]


@dataclass(frozen=True)
class BoundarySyncResult:
    previous_mode: StudentBoundaryMode
    new_mode: StudentBoundaryMode
    mode_changed: bool
    escalated: bool
    reason: str
    signals: dict[str, int]
    message: str | None


def _default_thresholds() -> dict[str, int]:
    # Intentionally simple MVP thresholds. We can expose per-tutor settings later.
    return {
        "reschedules_30d_yellow": 2,
        "reschedules_30d_orange": 3,
        "no_show_60d_orange": 1,
        "no_show_60d_red": 2,
        "late_30d_yellow": 2,  # late_minutes >= 10
        "late_30d_orange": 3,
        "unpaid_past_orange": 1,  # past lessons not paid and not cancelled/rescheduled
        "unpaid_past_red": 2,
    }


def _count_boundary_signals(
    db: Session, tutor_id: int, student_id: int, *, d30: date, d60: date, today: date
) -> dict[str, int]:
    cancelled = LessonStatus.cancelled.value
    rescheduled = LessonStatus.rescheduled.value
    no_show = LessonStatus.no_show.value

    row = (
        db.query(
            func.coalesce(
                func.sum(
                    case(
                        (and_(Lesson.status == rescheduled, Lesson.lesson_date >= d30), 1),
                        else_=0,
                    )
                ),
                0,
            ).label("reschedules_30d"),
            func.coalesce(
                func.sum(
                    case(
                        (and_(Lesson.status == no_show, Lesson.lesson_date >= d60), 1),
                        else_=0,
                    )
                ),
                0,
            ).label("no_show_60d"),
            func.coalesce(
                func.sum(
                    case(
                        (and_(Lesson.late_minutes >= 10, Lesson.lesson_date >= d30), 1),
                        else_=0,
                    )
                ),
                0,
            ).label("late_30d"),
            func.coalesce(
                func.sum(
                    case(
                        (
                            and_(
                                Lesson.is_paid.is_(False),
                                Lesson.lesson_date < today,
                                Lesson.status != cancelled,
                                Lesson.status != rescheduled,
                            ),
                            1,
                        ),
                        else_=0,
                    )
                ),
                0,
            ).label("unpaid_past"),
        )
        .filter(Lesson.tutor_id == tutor_id, Lesson.student_id == student_id)
        .one()
    )
    return {
        "reschedules_30d": int(row.reschedules_30d or 0),
        "no_show_60d": int(row.no_show_60d or 0),
        "late_30d": int(row.late_30d or 0),
        "unpaid_past": int(row.unpaid_past or 0),
    }


def decide_boundary_mode(db: Session, tutor_id: int, student_id: int) -> BoundaryDecision:
    today = date.today()
    d30 = today - timedelta(days=30)
    d60 = today - timedelta(days=60)
    t = _default_thresholds()

    signals = _count_boundary_signals(db, tutor_id, student_id, d30=d30, d60=d60, today=today)
    reschedules_30d = signals["reschedules_30d"]
    no_show_60d = signals["no_show_60d"]
    late_30d = signals["late_30d"]
    unpaid_past = signals["unpaid_past"]

    # Determine strictest mode that matches.
    if unpaid_past >= t["unpaid_past_red"] or no_show_60d >= t["no_show_60d_red"]:
        mode = StudentBoundaryMode.red
    elif (
        unpaid_past >= t["unpaid_past_orange"]
        or reschedules_30d >= t["reschedules_30d_orange"]
        or no_show_60d >= t["no_show_60d_orange"]
        or late_30d >= t["late_30d_orange"]
    ):
        mode = StudentBoundaryMode.orange
    elif reschedules_30d >= t["reschedules_30d_yellow"] or late_30d >= t["late_30d_yellow"]:
        mode = StudentBoundaryMode.yellow
    else:
        mode = StudentBoundaryMode.normal

    parts: list[str] = []
    if unpaid_past:
        parts.append(f"неоплаченных прошедших занятий: {unpaid_past}")
    if reschedules_30d:
        parts.append(f"переносов за 30 дней: {reschedules_30d}")
    if late_30d:
        parts.append(f"опозданий (10+ мин) за 30 дней: {late_30d}")
    if no_show_60d:
        parts.append(f"неявок за 60 дней: {no_show_60d}")

    reason = "; ".join(parts) if parts else "поведенческих сигналов риска нет"
    return BoundaryDecision(mode=mode, reason=reason, signals=signals)


def _get_student_or_raise(db: Session, tutor_id: int, student_id: int) -> Student:
    student = (
        db.query(Student)
        .filter(Student.id == student_id, Student.tutor_id == tutor_id)
        .first()
    )
    if not student:
        raise ValueError("Student not found")
    return student


def _parse_mode(raw: str | None) -> StudentBoundaryMode:
    value = (raw or StudentBoundaryMode.normal.value).strip().lower()
    try:
        return StudentBoundaryMode(value)
    except ValueError:
        return StudentBoundaryMode.normal


def render_boundary_message(
    student_name: str,
    mode: StudentBoundaryMode,
    reason: str,
    *,
    escalated: bool = True,
) -> str:
    if mode == StudentBoundaryMode.normal:
        if escalated:
            return ""
        return (
            "Привет! Возвращаемся к обычному формату занятий — спасибо, что держим график стабильно. "
            "Если что-то изменится, напиши заранее."
        )

    rules = BOUNDARY_RULES[mode]
    greeting = f"Привет, {student_name}!" if student_name else "Привет!"
    reason_line = ""
    if reason and reason != "поведенческих сигналов риска нет":
        reason_line = f"\n\nПричина: {reason}."
    return (
        f"{greeting} Чтобы график не разваливался и результат не терялся, "
        f"фиксирую правила на ближайшее время.{reason_line}\n\n"
        f"Правила:\n"
        f"• Перенос — {rules['reschedule_notice']}.\n"
        f"• Оплата — {rules['payment']}.\n"
        f"• Слоты — {rules['slots']}.\n\n"
        f"Так я гарантирую стабильный слот и прогресс. Ок?"
    )


def sync_student_boundaries(db: Session, tutor_id: int, student_id: int) -> BoundarySyncResult:
    student = _get_student_or_raise(db, tutor_id, student_id)
    decision = decide_boundary_mode(db, tutor_id, student_id)
    previous = _parse_mode(student.boundary_mode)
    new_mode = decision.mode
    escalated = MODE_SEVERITY[new_mode] > MODE_SEVERITY[previous]
    mode_changed = new_mode != previous

    message: str | None = None
    if mode_changed:
        student.boundary_mode = new_mode.value
        student.boundary_reason = decision.reason
        student.boundary_updated_at = datetime.utcnow()
        if escalated and new_mode != StudentBoundaryMode.normal:
            message = render_boundary_message(
                student.name, new_mode, decision.reason, escalated=True
            )
        elif not escalated and previous != StudentBoundaryMode.normal:
            message = render_boundary_message(
                student.name, new_mode, decision.reason, escalated=False
            )

    return BoundarySyncResult(
        previous_mode=previous,
        new_mode=new_mode,
        mode_changed=mode_changed,
        escalated=escalated,
        reason=decision.reason,
        signals=decision.signals,
        message=message,
    )


def apply_boundary_mode(
    db: Session, tutor_id: int, student_id: int, mode: StudentBoundaryMode, reason: str
) -> Student:
    student = _get_student_or_raise(db, tutor_id, student_id)
    student.boundary_mode = mode.value
    student.boundary_reason = reason
    student.boundary_updated_at = datetime.utcnow()
    db.commit()
    db.refresh(student)
    return student

