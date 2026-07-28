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
    from app.services.daily_challenge import normalize_avatar, normalize_theme

    hide = bool(getattr(tutor, "hide_balance_in_portal", True)) if tutor else True
    tg = (tutor.contact_telegram if tutor else "") or ""
    nick = (getattr(student, "portal_nickname", "") or "").strip()
    return {
        "id": student.id,
        "name": student.name,
        "display_name": nick or student.name,
        "subject": student.subject or "",
        "grade": student.grade or "",
        "balance": 0.0 if hide else float(student.balance or 0),
        "show_balance": not hide,
        "tutor_name": tutor.name if tutor else "",
        "tutor_telegram": tg,
        "tutor_contact_url": (tutor.contact_url if tutor else "") or "",
        "tutor_telegram_url": telegram_url(tg),
        "portal_nickname": nick,
        "portal_theme": normalize_theme(getattr(student, "portal_theme", None)),
        "portal_avatar": normalize_avatar(getattr(student, "portal_avatar", None)),
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

    from app.services.daily_challenge import daily_activity_dates

    activity_days = sorted(daily_activity_dates(db, student.id), reverse=True)
    streak = 0
    cursor = date.today()
    streak_at_risk = False
    if activity_days and activity_days[0] < cursor - timedelta(days=1):
        streak = 0
    else:
        if activity_days and activity_days[0] == cursor - timedelta(days=1):
            streak_at_risk = True
            cursor = activity_days[0]
        elif activity_days and activity_days[0] == cursor:
            streak_at_risk = False
        for d in activity_days:
            if d == cursor:
                streak += 1
                cursor = cursor - timedelta(days=1)
            elif d < cursor:
                break
        if streak > 0 and date.today() not in set(activity_days):
            streak_at_risk = True

    topics: list[str] = []
    topic_scores: dict[str, list[int]] = {}
    if lesson_ids:
        items = (
            db.query(ChecklistItem.topic, Lesson.id)
            .join(Lesson, ChecklistItem.lesson_id == Lesson.id)
            .filter(Lesson.student_id == student.id, Lesson.is_conducted.is_(True))
            .order_by(Lesson.lesson_date.desc())
            .limit(80)
            .all()
        )
        lesson_topics: dict[int, list[str]] = {}
        seen: set[str] = set()
        for topic, lid in items:
            t = (topic or "").strip()
            if not t:
                continue
            lesson_topics.setdefault(lid, []).append(t)
            if t.lower() not in seen:
                seen.add(t.lower())
                topics.append(t)
            if len(topics) >= 12:
                break

        hw_by_lesson = {h.lesson_id: h for h in homeworks}
        for lid, tlist in lesson_topics.items():
            hw = hw_by_lesson.get(lid)
            if not hw:
                continue
            st = by_hw.get(hw.id)
            if not st or st.ai_score is None or st.ai_review_status != "done":
                continue
            for t in tlist:
                topic_scores.setdefault(t, []).append(int(st.ai_score))

    topic_heat: list[dict] = []
    for t, vals in topic_scores.items():
        if not vals:
            continue
        avg_t = round(sum(vals) / len(vals), 1)
        if avg_t >= 75:
            level = "strong"
        elif avg_t >= 50:
            level = "ok"
        else:
            level = "weak"
        topic_heat.append(
            {"topic": t, "avg_score": avg_t, "samples": len(vals), "level": level}
        )
    topic_heat.sort(key=lambda x: x["avg_score"])

    weak = [x["topic"] for x in topic_heat if x["level"] == "weak"][:3]
    if weak:
        review_hint = "На следующем уроке повторить: " + ", ".join(weak)
    elif topics:
        review_hint = f"Сейчас в фокусе: {topics[0]}"
    else:
        review_hint = ""

    avg = round(sum(scores) / len(scores), 1) if scores else None
    return {
        "homework_total": len(homeworks),
        "homework_submitted": submitted,
        "homework_reviewed": reviewed,
        "homework_needs_revision": needs_rev,
        "streak_days": streak,
        "streak_at_risk": bool(streak_at_risk and streak > 0),
        "avg_ai_score": avg,
        "topics": topics,
        "topic_heat": topic_heat[:10],
        "recent_scores": recent[:8],
        "review_hint": review_hint,
    }
