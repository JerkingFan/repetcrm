"""Daily micro-practice challenges for streak days without lessons."""

from __future__ import annotations

import hashlib
import json
import logging
import random
import re
from datetime import date, datetime

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import Lesson, LessonStatus, Student, StudentDailyChallenge
from app.services.openrouter_client import _call_openrouter, is_configured as openrouter_configured

logger = logging.getLogger(__name__)

# (topic, question, expected_hint) — hint is for the AI checker only
_BANK: dict[str, list[tuple[str, str, str]]] = {
    "math": [
        ("Арифметика", "Сколько будет 17 × 4?", "68"),
        ("Дроби", "Чему равна 3/4 от 20?", "15"),
        ("Проценты", "Сколько это 20% от 250?", "50"),
        ("Уравнения", "Найди x: 2x + 5 = 17", "x = 6"),
        ("Степени", "Чему равно 2³?", "8"),
        ("Геометрия", "Площадь прямоугольника 5×8?", "40"),
        ("Корни", "Чему равен √81?", "9"),
        ("Отрицательные", "Чему равно −3 + 11?", "8"),
        ("Дроби", "Упрости 6/8", "3/4"),
        ("Логарифмы intro", "Чему равно log₁₀(100)?", "2"),
        ("Скорость", "Авто проехало 120 км за 2 часа. Средняя скорость?", "60 км/ч"),
        ("Пропорции", "Если 3 яблока стоят 90, сколько стоят 5?", "150"),
    ],
    "english": [
        ("Vocabulary", "Translate to English: «яблоко»", "apple"),
        ("Tenses", "Past tense of «go»?", "went"),
        ("Vocabulary", "Opposite of «hot»?", "cold / cool"),
        ("Grammar", "Fill in: She ___ (be) a student. Present.", "is"),
        ("Vocabulary", "Translate: «Thank you» → Russian", "спасибо"),
        ("Irregular", "Past tense of «write»?", "wrote"),
        ("Articles", "a or an before «hour»?", "an"),
        ("Plural", "Plural of «child»?", "children"),
    ],
    "russian": [
        ("Орфография", "Как правильно: «придти» или «прийти»?", "прийти"),
        ("Синтаксис", "Сколько главных членов в предложении «Солнце светит»?", "2 (подлежащее и сказуемое)"),
        ("Части речи", "Какая часть речи слово «быстро»?", "наречие"),
        ("Падежи", "В каком падеже слово «друзей» в «нет друзей»?", "родительный"),
        ("Орфография", "Как правильно: «здесь» или «сдесь»?", "здесь"),
    ],
    "physics": [
        ("Механика", "Формула скорости: v = ?", "v = s/t (путь/время)"),
        ("Единицы", "В чём измеряется сила в СИ?", "ньютон (Н)"),
        ("Электричество", "Обозначение силы тока?", "I"),
        ("Оптика", "Скорость света в вакууме примерно?", "3·10⁸ м/с"),
    ],
    "general": [
        ("Логика", "Продолжи: 2, 4, 8, 16, …", "32"),
        ("Логика", "Сколько будет 100 − 37?", "63"),
        ("Память", "Сколько дней в неделе?", "7"),
        ("Логика", "Если все розы цветы, а некоторые цветы вянут — все ли розы вянут? (да/нет/неизвестно)", "неизвестно"),
    ],
}

_PORTAL_THEMES = {"ocean", "forest", "sunset", "midnight", "candy"}
_PORTAL_AVATARS = {"rocket", "fox", "cat", "owl", "dragon", "star", "book", "bolt"}


def normalize_theme(value: str | None) -> str:
    v = (value or "ocean").strip().lower()
    return v if v in _PORTAL_THEMES else "ocean"


def normalize_avatar(value: str | None) -> str:
    v = (value or "rocket").strip().lower()
    return v if v in _PORTAL_AVATARS else "rocket"


def _subject_key(subject: str) -> str:
    s = (subject or "").lower()
    if any(x in s for x in ("матем", "алгебр", "геометр", "math")):
        return "math"
    if any(x in s for x in ("англ", "english", "eng")):
        return "english"
    if any(x in s for x in ("русск", "литерат")):
        return "russian"
    if any(x in s for x in ("физик", "phys")):
        return "physics"
    return "general"


def has_lesson_today(db: Session, student_id: int, today: date | None = None) -> bool:
    today = today or date.today()
    row = (
        db.query(Lesson.id)
        .filter(
            Lesson.student_id == student_id,
            Lesson.lesson_date == today,
            Lesson.status != LessonStatus.cancelled.value,
        )
        .first()
    )
    return row is not None


def _pick_from_bank(student: Student, today: date) -> tuple[str, str, str]:
    key = _subject_key(student.subject)
    pool = list(_BANK.get(key) or []) + list(_BANK["general"])
    # Stable-ish randomness per student+day so refresh doesn't reshuffle mid-day
    seed = int(hashlib.sha256(f"{student.id}:{today.isoformat()}".encode()).hexdigest()[:8], 16)
    rng = random.Random(seed)
    return rng.choice(pool)


async def _maybe_ai_question(student: Student) -> tuple[str, str, str] | None:
    if not openrouter_configured():
        return None
    subject = student.subject or "школьный предмет"
    grade = student.grade or ""
    prompt = (
        f"Сгенерируй ОДНУ короткую учебную задачу для ученика ({subject}"
        f"{', класс ' + grade if grade else ''}). "
        "Ответ — одно число/слово/короткая фраза. "
        'Верни строго JSON: {"topic":"...","question":"...","expected_hint":"правильный ответ"}'
    )
    try:
        raw = await _call_openrouter(
            [
                {"role": "system", "content": "Ты учитель. Только JSON без markdown."},
                {"role": "user", "content": prompt},
            ]
        )
        text = raw.strip()
        if text.startswith("```"):
            text = re.sub(r"^```(?:json)?\s*", "", text)
            text = re.sub(r"\s*```$", "", text)
        data = json.loads(text)
        q = str(data.get("question") or "").strip()
        topic = str(data.get("topic") or "Практика").strip()[:255]
        hint = str(data.get("expected_hint") or "").strip()
        if len(q) >= 5:
            return topic, q, hint
    except Exception as e:
        logger.info("daily challenge AI generate skipped: %s", e)
    return None


async def ensure_today_challenge(db: Session, student: Student) -> dict:
    """Return today's challenge state. Creates one if no lesson today."""
    today = date.today()
    existing = (
        db.query(StudentDailyChallenge)
        .filter(
            StudentDailyChallenge.student_id == student.id,
            StudentDailyChallenge.challenge_date == today,
        )
        .first()
    )
    if existing:
        return _challenge_out(existing, lesson_today=has_lesson_today(db, student.id, today))

    lesson_today = has_lesson_today(db, student.id, today)
    if lesson_today:
        return {
            "available": False,
            "reason": "lesson_today",
            "message": "Сегодня урок — стрик можно закрыть сдачей ДЗ или после занятия",
            "challenge": None,
        }

    ai = await _maybe_ai_question(student)
    if ai:
        topic, question, hint = ai
    else:
        topic, question, hint = _pick_from_bank(student, today)

    row = StudentDailyChallenge(
        student_id=student.id,
        challenge_date=today,
        question=question,
        topic=topic,
        difficulty="easy",
        expected_hint=hint,
        status="open",
    )
    db.add(row)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        existing = (
            db.query(StudentDailyChallenge)
            .filter(
                StudentDailyChallenge.student_id == student.id,
                StudentDailyChallenge.challenge_date == today,
            )
            .first()
        )
        if existing:
            return _challenge_out(existing, lesson_today=False)
        raise
    db.refresh(row)
    return _challenge_out(row, lesson_today=False)


def _challenge_out(row: StudentDailyChallenge, *, lesson_today: bool) -> dict:
    return {
        "available": True,
        "reason": "",
        "message": "",
        "lesson_today": lesson_today,
        "challenge": {
            "id": row.id,
            "challenge_date": row.challenge_date.isoformat(),
            "question": row.question,
            "topic": row.topic,
            "difficulty": row.difficulty,
            "status": row.status,
            "answer_text": row.answer_text or "",
            "ai_verdict": row.ai_verdict or "",
            "ai_score": row.ai_score,
            "ai_feedback": row.ai_feedback or "",
            "answered_at": row.answered_at.isoformat() if row.answered_at else None,
        },
    }


async def check_daily_answer(db: Session, student: Student, challenge_id: int, answer: str) -> dict:
    row = (
        db.query(StudentDailyChallenge)
        .filter(
            StudentDailyChallenge.id == challenge_id,
            StudentDailyChallenge.student_id == student.id,
        )
        .first()
    )
    if not row:
        raise ValueError("not_found")
    # Already correct — return as-is; incorrect stays retryable same day
    if row.status == "correct":
        return _challenge_out(row, lesson_today=has_lesson_today(db, student.id))

    text = (answer or "").strip()
    if len(text) < 1:
        raise ValueError("empty")

    verdict, score, feedback = await _grade_answer(row, text)
    row.answer_text = text[:2000]
    row.ai_verdict = verdict
    row.ai_score = score
    row.ai_feedback = feedback[:2000]
    row.status = "correct" if verdict == "correct" else "incorrect"
    row.answered_at = datetime.utcnow()
    db.commit()
    db.refresh(row)
    return _challenge_out(row, lesson_today=has_lesson_today(db, student.id))


async def _grade_answer(row: StudentDailyChallenge, answer: str) -> tuple[str, int, str]:
    # Fast path: exact / normalized match to hint
    hint = (row.expected_hint or "").strip().lower()
    ans = answer.strip().lower()
    if hint:
        hint_num = re.sub(r"[^\d.,\-/=xх]", "", hint.replace(",", "."))
        ans_num = re.sub(r"[^\d.,\-/=xх]", "", ans.replace(",", "."))
        if hint == ans or (hint_num and hint_num == ans_num):
            return "correct", 100, "Верно!"
        # allow "x = 6" vs "6"
        if hint_num and (hint_num in ans_num or ans_num in hint_num):
            return "correct", 95, "Верно!"

    if openrouter_configured():
        try:
            raw = await _call_openrouter(
                [
                    {
                        "role": "system",
                        "content": (
                            "Ты проверяешь короткий ответ ученика. "
                            'Верни JSON: {"verdict":"correct|incorrect|partial","score":0-100,"feedback":"1-2 предложения по-русски"}'
                        ),
                    },
                    {
                        "role": "user",
                        "content": (
                            f"Задача: {row.question}\n"
                            f"Ожидаемый ответ (подсказка): {row.expected_hint or '—'}\n"
                            f"Ответ ученика: {answer}"
                        ),
                    },
                ]
            )
            text = raw.strip()
            if text.startswith("```"):
                text = re.sub(r"^```(?:json)?\s*", "", text)
                text = re.sub(r"\s*```$", "", text)
            data = json.loads(text)
            verdict = str(data.get("verdict") or "incorrect").lower()
            if verdict not in ("correct", "incorrect", "partial"):
                verdict = "incorrect"
            if verdict == "partial":
                verdict = "incorrect"
            score = int(data.get("score") or 0)
            score = max(0, min(100, score))
            if verdict == "correct" and score < 70:
                score = 80
            feedback = str(data.get("feedback") or "").strip() or (
                "Верно!" if verdict == "correct" else "Пока неверно — попробуй ещё раз завтра или спроси репетитора."
            )
            return verdict, score, feedback
        except Exception as e:
            logger.info("daily challenge AI grade fallback: %s", e)

    # Fallback without AI
    if hint and hint[:3] in ans:
        return "correct", 80, "Похоже на верный ответ."
    return (
        "incorrect",
        0,
        f"Пока не сходится. Подсказка: правильный ответ ближе к «{row.expected_hint or '…'}».",
    )


def daily_activity_dates(db: Session, student_id: int) -> set[date]:
    """Dates that count toward streak: HW submissions + correct daily challenges."""
    from app.models import HomeworkSubmission

    days: set[date] = set()
    for row in (
        db.query(HomeworkSubmission.submitted_at)
        .filter(HomeworkSubmission.student_id == student_id)
        .all()
    ):
        d = row[0]
        if not d:
            continue
        days.add(d.date() if hasattr(d, "date") else d)
    for row in (
        db.query(StudentDailyChallenge.challenge_date)
        .filter(
            StudentDailyChallenge.student_id == student_id,
            StudentDailyChallenge.status == "correct",
        )
        .all()
    ):
        d = row[0]
        if d:
            days.add(d)
    return days
