"""AI review of student homework photo submissions via OpenRouter vision."""

from __future__ import annotations

import asyncio
import base64
import json
import logging
import os
import re
from datetime import datetime

from sqlalchemy.orm import Session, joinedload

from app.config import get_settings
from app.database import SessionLocal
from app.models import Homework, HomeworkSubmission, Lesson, Student
from app.services.openrouter_client import OpenRouterError, call_openrouter_vision, is_configured

logger = logging.getLogger(__name__)

_IMAGE_MIME = {"image/jpeg", "image/png", "image/webp", "image/heic", "image/heif"}
_VERDICTS = {"correct", "partially_correct", "incorrect", "unclear"}

VERDICT_LABELS: dict[str, str] = {
    "correct": "Верно",
    "partially_correct": "Частично верно",
    "incorrect": "Неверно",
    "unclear": "Не удалось оценить",
}


def verdict_label(verdict: str) -> str:
    return VERDICT_LABELS.get(verdict, verdict or "—")


def _strip_html(text: str) -> str:
    clean = re.sub(r"<[^>]+>", " ", text or "")
    return " ".join(clean.split())


def _parse_ai_json(raw: str) -> dict:
    text = (raw or "").strip()
    fence = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
    if fence:
        text = fence.group(1).strip()
    data = json.loads(text)
    if not isinstance(data, dict):
        raise ValueError("AI response is not a JSON object")
    return data


def _normalize_verdict(value: str) -> str:
    v = (value or "").strip().lower().replace("-", "_").replace(" ", "_")
    aliases = {
        "partial": "partially_correct",
        "partially": "partially_correct",
        "partiallycorrect": "partially_correct",
        "wrong": "incorrect",
        "right": "correct",
        "ok": "correct",
    }
    v = aliases.get(v, v)
    return v if v in _VERDICTS else "unclear"


def _image_data_url(file_path: str, mime: str) -> str:
    cfg = get_settings()
    max_bytes = min(cfg.homework_submission_max_bytes, 4 * 1024 * 1024)
    with open(file_path, "rb") as f:
        content = f.read(max_bytes + 1)
    if len(content) > max_bytes:
        content = content[:max_bytes]
    b64 = base64.standard_b64encode(content).decode("ascii")
    return f"data:{mime};base64,{b64}"


def _build_prompt(*, homework_text: str, student: Student, comment: str) -> str:
    assignment = _strip_html(homework_text)[:6000]
    student_note = (comment or "").strip()[:500]
    parts = [
        "Задание для ученика:",
        assignment or "(текст задания недоступен)",
        "",
        f"Ученик: {student.name}, предмет: {student.subject or '—'}, класс: {student.grade or '—'}.",
    ]
    if student_note:
        parts.extend(["", f"Комментарий ученика: {student_note}"])
    parts.extend(
        [
            "",
            "На фото — решение ученика. Сравни с заданием и оцени правильность.",
            "Ответь ТОЛЬКО валидным JSON без markdown:",
            '{',
            '  "verdict": "correct" | "partially_correct" | "incorrect" | "unclear",',
            '  "score": 0-100,',
            '  "feedback": "краткий комментарий ученику на русском (2-4 предложения)"',
            "}",
        ]
    )
    return "\n".join(parts)


async def review_submission_ai(submission_id: int) -> None:
    cfg = get_settings()
    db = SessionLocal()
    try:
        sub = (
            db.query(HomeworkSubmission)
            .options(
                joinedload(HomeworkSubmission.homework).joinedload(Homework.lesson).joinedload(Lesson.student),
            )
            .filter(HomeworkSubmission.id == submission_id)
            .first()
        )
        if not sub:
            return

        sub.ai_review_status = "running"
        db.commit()

        mime = (sub.mime_type or "").split(";")[0].strip().lower()
        if mime not in _IMAGE_MIME:
            sub.ai_review_status = "skipped"
            sub.ai_feedback = (
                "Автопроверка работает только с фото (JPG, PNG, WebP). "
                "PDF проверит репетитор вручную."
            )
            sub.ai_reviewed_at = datetime.utcnow()
            db.commit()
            return

        if not cfg.homework_ai_review_enabled or not is_configured():
            sub.ai_review_status = "skipped"
            sub.ai_feedback = "Автопроверка недоступна — репетитор проверит вручную."
            sub.ai_reviewed_at = datetime.utcnow()
            db.commit()
            return

        full_path = os.path.join(cfg.media_dir, sub.file_path)
        if not os.path.isfile(full_path):
            sub.ai_review_status = "error"
            sub.ai_review_error = "Файл решения не найден"
            sub.ai_reviewed_at = datetime.utcnow()
            db.commit()
            return

        homework = sub.homework
        student = homework.lesson.student if homework and homework.lesson else None
        if not homework or not student:
            sub.ai_review_status = "error"
            sub.ai_review_error = "Не удалось загрузить задание"
            sub.ai_reviewed_at = datetime.utcnow()
            db.commit()
            return

        prompt = _build_prompt(
            homework_text=homework.homework_text,
            student=student,
            comment=sub.comment,
        )
        image_url = _image_data_url(full_path, mime)
        system = (
            "Ты — помощник репетитора. Оцениваешь решения учеников по фото. "
            "Будь доброжелателен, но честен. Если фото нечитаемо — verdict=unclear. "
            "Отвечай только JSON."
        )

        raw = await call_openrouter_vision(
            system_prompt=system,
            user_prompt=prompt,
            image_data_url=image_url,
        )
        data = _parse_ai_json(raw)
        verdict = _normalize_verdict(str(data.get("verdict", "")))
        score_raw = data.get("score")
        score: int | None
        try:
            score = max(0, min(100, int(score_raw)))
        except (TypeError, ValueError):
            score = None
        feedback = str(data.get("feedback", "") or "").strip()[:2000]

        sub.ai_review_status = "done"
        sub.ai_verdict = verdict
        sub.ai_score = score
        sub.ai_feedback = feedback or verdict_label(verdict)
        sub.ai_review_error = ""
        sub.ai_reviewed_at = datetime.utcnow()
        db.commit()
        logger.info(
            "AI review done submission=%s verdict=%s score=%s",
            submission_id,
            verdict,
            score,
        )
    except (OpenRouterError, json.JSONDecodeError, ValueError) as e:
        logger.warning("AI review failed submission=%s: %s", submission_id, e)
        db.rollback()
        sub = db.query(HomeworkSubmission).filter(HomeworkSubmission.id == submission_id).first()
        if sub:
            sub.ai_review_status = "error"
            sub.ai_review_error = str(e)[:500]
            sub.ai_reviewed_at = datetime.utcnow()
            db.commit()
    except Exception:
        logger.exception("AI review unexpected error submission=%s", submission_id)
        db.rollback()
        sub = db.query(HomeworkSubmission).filter(HomeworkSubmission.id == submission_id).first()
        if sub:
            sub.ai_review_status = "error"
            sub.ai_review_error = "Внутренняя ошибка автопроверки"
            sub.ai_reviewed_at = datetime.utcnow()
            db.commit()
    finally:
        db.close()


def schedule_ai_review(submission_id: int) -> None:
    """Fire-and-forget background AI review."""
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        asyncio.run(review_submission_ai(submission_id))
        return
    loop.create_task(review_submission_ai(submission_id))


def mark_submission_pending_ai(db: Session, submission: HomeworkSubmission) -> None:
    cfg = get_settings()
    mime = (submission.mime_type or "").split(";")[0].strip().lower()
    if not cfg.homework_ai_review_enabled:
        submission.ai_review_status = "skipped"
        submission.ai_feedback = "Автопроверка отключена — репетитор проверит вручную."
        return
    if mime not in _IMAGE_MIME:
        submission.ai_review_status = "skipped"
        submission.ai_feedback = (
            "Автопроверка работает только с фото (JPG, PNG, WebP). "
            "PDF проверит репетитор вручную."
        )
        return
    if not is_configured():
        submission.ai_review_status = "skipped"
        submission.ai_feedback = "Автопроверка недоступна — репетитор проверит вручную."
        return
    submission.ai_review_status = "pending"
    submission.ai_verdict = ""
    submission.ai_score = None
    submission.ai_feedback = ""
    submission.ai_review_error = ""
    submission.ai_reviewed_at = None
