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
from app.services.homework_output import homework_plain_preview, is_latex_document, _extract_task_bodies
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


def _assignment_for_prompt(homework_text: str) -> str:
    """Читаемое задание без LaTeX-преамбулы — иначе модель «не узнаёт» задачи."""
    text = (homework_text or "").strip()
    if not text:
        return "(текст задания недоступен)"

    if is_latex_document(text):
        tasks = [t for t in _extract_task_bodies(text) if t.strip()]
        if tasks:
            lines = [f"{i}. {re.sub(r'\s+', ' ', t).strip()}" for i, t in enumerate(tasks[:12], 1)]
            return "Задачи:\n" + "\n".join(lines)

    preview, _n = homework_plain_preview(text, max_len=2500)
    if preview and "documentclass" not in preview.lower() and "usepackage" not in preview.lower():
        return preview

    # HTML → plain
    clean = re.sub(r"<[^>]+>", "\n", text)
    clean = re.sub(r"\\[a-zA-Z]+\*?(\[[^\]]*\])?(\{[^}]*\})?", " ", clean)
    clean = " ".join(clean.split())
    return clean[:2500] if clean else "(текст задания недоступен)"


def _parse_ai_json(raw: str) -> dict:
    text = (raw or "").strip()
    fence = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
    if fence:
        text = fence.group(1).strip()
    # иногда модель добавляет текст до/после JSON
    brace = re.search(r"\{[\s\S]*\}", text)
    if brace:
        text = brace.group(0)
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
        "illegible": "unclear",
        "unreadable": "unclear",
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
    assignment = _assignment_for_prompt(homework_text)
    student_note = (comment or "").strip()[:500]
    parts = [
        "Ниже — условия домашних задач (уже очищены от LaTeX-разметки).",
        "На приложенном фото — рукописное или сфотографированное решение ученика.",
        "",
        assignment,
        "",
        f"Ученик: {student.name}. Предмет: {student.subject or '—'}. Класс: {student.grade or '—'}.",
    ]
    if student_note:
        parts.extend(["", f"Комментарий ученика: {student_note}"])
    parts.extend(
        [
            "",
            "Правила оценки:",
            "- Смотри на фото внимательно: цифры, формулы, шаги решения.",
            "- Если текст на фото читается хотя бы частично — оценивай по существу, НЕ ставь unclear.",
            "- unclear только если фото совсем чёрное/смазано/пустая страница и разобрать нельзя.",
            "- Не пиши шаблонные фразы вроде «не соответствует заданию», если не уверен — укажи конкретно, какая задача и что не так.",
            "- feedback: конкретно, доброжелательно, на русском, 2–4 предложения.",
            "- score: 0–100 (для unclear поставь null).",
            "",
            "Ответь ТОЛЬКО JSON:",
            '{"verdict":"correct"|"partially_correct"|"incorrect"|"unclear","score":0-100|null,"feedback":"..."}',
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
            "Ты — опытный репетитор. Проверяешь фото решения ученика. "
            "Это реальная проверка, не заглушка: опирайся на то, что видно на фото и на список задач. "
            "Будь конкретным. Отвечай только JSON."
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
        if score_raw is None or (isinstance(score_raw, str) and score_raw.strip().lower() in ("", "null", "none")):
            score = None
        else:
            try:
                score = max(0, min(100, int(float(score_raw))))
            except (TypeError, ValueError):
                score = None
        # unclear + 0% выглядит как заглушка — убираем процент
        if verdict == "unclear":
            score = None

        feedback = str(data.get("feedback", "") or "").strip()[:2000]
        if verdict == "unclear" and not feedback:
            feedback = (
                "Не удалось уверенно разобрать решение на фото. "
                "Попробуй переснять при хорошем свете, без бликов, или дождись проверки репетитора."
            )

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
