"""Helpers for student portal: meeting links, boards, tutor contact."""

from __future__ import annotations

import re
from datetime import date, timedelta
from typing import Callable

from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import Board, HomeworkSubmission, Lesson, LessonRescheduleRequest, LessonStatus, Student, User

_URL_RE = re.compile(r"https?://[^\s<>\"']+", re.I)


def extract_url_from_text(text: str) -> str:
    if not text:
        return ""
    m = _URL_RE.search(text)
    return (m.group(0).rstrip(".,);]") if m else "")[:500]


def resolve_meeting_url(lesson: Lesson, tutor: User | None = None) -> str:
    url = (getattr(lesson, "meeting_url", None) or "").strip()
    if url:
        return url[:500]
    from_notes = extract_url_from_text(lesson.notes or "")
    if from_notes:
        return from_notes
    if tutor and (tutor.contact_url or "").strip():
        return tutor.contact_url.strip()[:500]
    return ""


def telegram_url(username: str) -> str:
    u = (username or "").strip().lstrip("@")
    if not u:
        return ""
    if u.startswith("http"):
        return u
    return f"https://t.me/{u}"


def board_public_url(board: Board | None) -> str:
    if not board or not board.share_token:
        return ""
    base = get_settings().public_site_url.rstrip("/")
    return f"{base}/board/{board.id}?token={board.share_token}"


def student_out_fields(student: Student, tutor: User | None) -> dict:
    hide = bool(getattr(tutor, "hide_balance_in_portal", True)) if tutor else True
    tg = (tutor.contact_telegram if tutor else "") or ""
    return {
        "id": student.id,
        "name": student.name,
        "subject": student.subject or "",
        "grade": student.grade or "",
        "balance": 0.0 if hide else float(student.balance or 0),
        "show_balance": not hide,
        "tutor_name": tutor.name if tutor else "",
        "tutor_telegram": tg,
        "tutor_contact_url": (tutor.contact_url if tutor else "") or "",
        "tutor_telegram_url": telegram_url(tg),
    }


def latest_reschedule_map(db: Session, student_id: int, lesson_ids: list[int]) -> dict[int, str]:
    if not lesson_ids:
        return {}
    rows = (
        db.query(LessonRescheduleRequest)
        .filter(
            LessonRescheduleRequest.student_id == student_id,
            LessonRescheduleRequest.lesson_id.in_(lesson_ids),
        )
        .order_by(LessonRescheduleRequest.created_at.desc())
        .all()
    )
    out: dict[int, str] = {}
    for r in rows:
        if r.lesson_id not in out:
            out[r.lesson_id] = r.status or "pending"
    return out


def default_homework_due_date(db: Session, lesson: Lesson) -> date:
    """Due by next lesson, or +3 days if no next lesson scheduled."""
    next_lesson = (
        db.query(Lesson)
        .filter(
            Lesson.student_id == lesson.student_id,
            Lesson.lesson_date > lesson.lesson_date,
            Lesson.status != LessonStatus.cancelled.value,
        )
        .order_by(Lesson.lesson_date.asc())
        .first()
    )
    if next_lesson:
        return next_lesson.lesson_date
    return lesson.lesson_date + timedelta(days=3)


def compute_progress(db: Session, student: Student) -> dict:
    from app.models import ChecklistItem, Homework

    lessons = (
        db.query(Lesson)
        .filter(Lesson.student_id == student.id)
        .order_by(Lesson.lesson_date.desc())
        .all()
    )
    lesson_ids = [l.id for l in lessons]
    homeworks = (
        db.query(Homework).filter(Homework.lesson_id.in_(lesson_ids)).all() if lesson_ids else []
    )
    hw_ids = [h.id for h in homeworks]
    subs = (
        db.query(HomeworkSubmission)
        .filter(
            HomeworkSubmission.student_id == student.id,
            HomeworkSubmission.homework_id.in_(hw_ids),
        )
        .order_by(HomeworkSubmission.submitted_at.desc())
        .all()
        if hw_ids
        else []
    )

    by_hw: dict[int, HomeworkSubmission] = {}
    for s in subs:
        if s.homework_id not in by_hw:
            by_hw[s.homework_id] = s

    submitted = reviewed = needs_rev = 0
    scores: list[int] = []
    recent: list[dict] = []
    for h in homeworks:
        st = by_hw.get(h.id)
        if not st:
            continue
        status = st.status or "submitted"
        if status == "reviewed":
            reviewed += 1
            submitted += 1
        elif status == "needs_revision":
            needs_rev += 1
            submitted += 1
        else:
            submitted += 1
        if st.ai_score is not None and st.ai_review_status == "done":
            scores.append(int(st.ai_score))
            recent.append(
                {
                    "homework_id": h.id,
                    "score": int(st.ai_score),
                    "verdict": st.ai_verdict or "",
                    "date": (st.submitted_at.date().isoformat() if st.submitted_at else ""),
                }
            )

    days = sorted({s.submitted_at.date() for s in subs if s.submitted_at}, reverse=True)
    streak = 0
    cursor = date.today()
    if days and days[0] < cursor - timedelta(days=1):
        streak = 0
    else:
        if days and days[0] == cursor - timedelta(days=1):
            cursor = days[0]
        for d in days:
            if d == cursor:
                streak += 1
                cursor = cursor - timedelta(days=1)
            elif d < cursor:
                break

    topics: list[str] = []
    if lesson_ids:
        items = (
            db.query(ChecklistItem.topic)
            .join(Lesson, ChecklistItem.lesson_id == Lesson.id)
            .filter(Lesson.student_id == student.id, Lesson.is_conducted.is_(True))
            .order_by(Lesson.lesson_date.desc())
            .limit(40)
            .all()
        )
        seen: set[str] = set()
        for (topic,) in items:
            t = (topic or "").strip()
            if t and t.lower() not in seen:
                seen.add(t.lower())
                topics.append(t)
            if len(topics) >= 12:
                break

    avg = round(sum(scores) / len(scores), 1) if scores else None
    return {
        "homework_total": len(homeworks),
        "homework_submitted": submitted,
        "homework_reviewed": reviewed,
        "homework_needs_revision": needs_rev,
        "streak_days": streak,
        "avg_ai_score": avg,
        "topics": topics,
        "recent_scores": recent[:8],
    }
