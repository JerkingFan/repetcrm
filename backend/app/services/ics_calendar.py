"""iCalendar (.ics) export for lessons."""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from typing import Iterable

from app.models import Lesson


def _escape_ics(text: str) -> str:
    return (
        text.replace("\\", "\\\\")
        .replace(";", "\\;")
        .replace(",", "\\,")
        .replace("\n", "\\n")
    )


def _lesson_dt(lesson_date: date, lesson_time: str) -> datetime:
    parts = (lesson_time or "10:00").split(":")
    hour = int(parts[0]) if parts else 10
    minute = int(parts[1]) if len(parts) > 1 else 0
    return datetime(lesson_date.year, lesson_date.month, lesson_date.day, hour, minute)


def build_ics(
    lessons: Iterable[Lesson],
    *,
    calendar_name: str,
    student_name: str | None = None,
) -> str:
    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//RepetCRM//Calendar//RU",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        f"X-WR-CALNAME:{_escape_ics(calendar_name)}",
    ]
    now = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")

    for lesson in lessons:
        start = _lesson_dt(lesson.lesson_date, lesson.lesson_time)
        end = start + timedelta(minutes=lesson.duration_minutes or 60)
        uid = f"lesson-{lesson.id}@repetcrm"
        title = f"Урок: {student_name or getattr(lesson.student, 'name', 'ученик')}"
        if lesson.student and not student_name:
            title = f"Урок: {lesson.student.name}"
        desc_parts = []
        if lesson.notes:
            desc_parts.append(lesson.notes)
        if lesson.payment_amount:
            desc_parts.append(f"Оплата: {lesson.payment_amount} Br ({'оплачено' if lesson.is_paid else 'не оплачено'})")
        description = _escape_ics(" · ".join(desc_parts))

        lines.extend(
            [
                "BEGIN:VEVENT",
                f"UID:{uid}",
                f"DTSTAMP:{now}",
                f"DTSTART:{start.strftime('%Y%m%dT%H%M%S')}",
                f"DTEND:{end.strftime('%Y%m%dT%H%M%S')}",
                f"SUMMARY:{_escape_ics(title)}",
                f"DESCRIPTION:{description}",
                "STATUS:CONFIRMED",
                "END:VEVENT",
            ]
        )

    lines.append("END:VCALENDAR")
    return "\r\n".join(lines) + "\r\n"
