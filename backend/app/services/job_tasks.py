"""Background job implementations (API in-process fallback + ARQ worker)."""

from __future__ import annotations

import asyncio
import logging
import time

from sqlalchemy.orm import Session, joinedload

from app.config import get_settings
from app.database import SessionLocal
from app.models import Homework, Lesson
from app.services.homework_ai import generate_homework_ai
from app.services.homework_prefs import apply_prefs_to_checklist, parse_homework_prefs
from app.services import job_store
from app.services.job_types import Job
from app.services.pdf import generate_homework_pdf, invalidate_homework_pdf
from app.services.smart_homework import generate_smart_homework_latex

logger = logging.getLogger(__name__)


def _now_ms() -> int:
    return int(time.time() * 1000)


def _mark_running(job_id: str) -> None:
    job = job_store.load_job(job_id)
    if not job:
        return
    job.status = "running"
    job.updated_at_ms = _now_ms()
    job_store.save_job(job)


def _mark_done(job_id: str, result: dict) -> None:
    job = job_store.load_job(job_id)
    if not job:
        return
    job.status = "done"
    job.result = result
    job.updated_at_ms = _now_ms()
    job_store.save_job(job)


def _mark_error(job_id: str, error: str) -> None:
    job = job_store.load_job(job_id)
    if not job:
        return
    job.status = "error"
    job.error = error
    job.updated_at_ms = _now_ms()
    job_store.save_job(job)


def _clear_active(job: Job | None) -> None:
    if not job:
        return
    if job.lesson_id is not None:
        job_store.clear_active(job.owner_user_id, "lesson", job.lesson_id)
    elif job.homework_id is not None:
        job_store.clear_active(job.owner_user_id, "homework", job.homework_id)


def _get_lesson(db: Session, lesson_id: int, tutor_id: int) -> Lesson | None:
    return (
        db.query(Lesson)
        .options(
            joinedload(Lesson.student),
            joinedload(Lesson.checklist_items),
            joinedload(Lesson.homework),
        )
        .filter(Lesson.id == lesson_id, Lesson.tutor_id == tutor_id)
        .first()
    )


def _get_homework(db: Session, homework_id: int, tutor_id: int) -> Homework | None:
    return (
        db.query(Homework)
        .join(Lesson)
        .options(
            joinedload(Homework.lesson).joinedload(Lesson.student),
            joinedload(Homework.lesson).joinedload(Lesson.checklist_items),
        )
        .filter(Homework.id == homework_id, Lesson.tutor_id == tutor_id)
        .first()
    )


def _lesson_checklist(lesson: Lesson) -> list[dict]:
    prefs = parse_homework_prefs(lesson.homework_prefs)
    return apply_prefs_to_checklist(
        [
            {
                "topic": i.topic,
                "work_type": i.work_type,
                "difficulty": i.difficulty,
                "understanding": i.understanding,
            }
            for i in lesson.checklist_items
        ],
        prefs,
    )


async def run_generate_homework(lesson_id: int, tutor_id: int) -> dict:
    cfg = get_settings()
    openrouter_cap_sec = 60.0

    db = SessionLocal()
    try:
        lesson = _get_lesson(db, lesson_id, tutor_id)
        if not lesson:
            raise ValueError("Lesson not found")
        if not lesson.is_conducted:
            raise ValueError("Занятие не отмечено проведённым")
        if not lesson.checklist_items:
            raise ValueError("Чек-лист пуст")

        prefs = parse_homework_prefs(lesson.homework_prefs)
        checklist = _lesson_checklist(lesson)

        try:
            html, source, hint = await asyncio.wait_for(
                generate_homework_ai(
                    lesson.student.name,
                    lesson.student.subject,
                    checklist,
                    lesson.student.grade,
                    homework_prefs=prefs,
                ),
                timeout=openrouter_cap_sec
                if cfg.homework_ai_provider in ("openrouter", "auto")
                else 900.0,
            )
        except Exception as e:
            html = generate_smart_homework_latex(
                lesson.student.name,
                lesson.student.subject,
                checklist,
                lesson.student.grade or "",
                homework_prefs=prefs,
            )
            source = "smart_fallback"
            hint = f"AI timeout/error: {e}. Использован шаблон."

        if lesson.homework:
            lesson.homework.homework_text = html
            hw = lesson.homework
        else:
            hw = Homework(lesson_id=lesson_id, homework_text=html)
            db.add(hw)
        db.commit()
        db.refresh(hw)
        invalidate_homework_pdf(hw.id)
        return {
            "homework_id": hw.id,
            "generation_source": source,
            "generation_hint": hint,
            "configured_provider": cfg.homework_ai_provider,
            "configured_model": cfg.openrouter_model,
        }
    finally:
        db.close()


async def run_build_pdf(homework_id: int, tutor_id: int) -> dict:
    db = SessionLocal()
    try:
        hw = _get_homework(db, homework_id, tutor_id)
        if not hw:
            raise ValueError("Homework not found")
        if not hw.homework_text.strip():
            raise ValueError("Домашнее задание пустое")

        lesson = hw.lesson
        prefs = parse_homework_prefs(lesson.homework_prefs)
        checklist = _lesson_checklist(lesson)
        path = await asyncio.to_thread(
            generate_homework_pdf,
            hw.id,
            lesson.student.name,
            lesson.lesson_date,
            hw.homework_text,
            subject=lesson.student.subject,
            checklist=checklist or None,
            grade=lesson.student.grade or "",
            homework_prefs=prefs,
        )
        return {"pdf_path": path, "homework_id": hw.id}
    finally:
        db.close()


async def generate_homework_task(ctx, job_id: str, lesson_id: int, tutor_id: int) -> None:
    job = job_store.load_job(job_id)
    _mark_running(job_id)
    try:
        result = await run_generate_homework(lesson_id, tutor_id)
        _mark_done(job_id, result)
        logger.info("generate_homework_task done job=%s lesson=%s", job_id, lesson_id)
    except Exception as e:
        logger.exception("generate_homework_task failed job=%s", job_id)
        _mark_error(job_id, str(e))
    finally:
        _clear_active(job)


async def build_pdf_task(ctx, job_id: str, homework_id: int, tutor_id: int) -> None:
    job = job_store.load_job(job_id)
    _mark_running(job_id)
    try:
        result = await run_build_pdf(homework_id, tutor_id)
        _mark_done(job_id, result)
        logger.info("build_pdf_task done job=%s homework=%s", job_id, homework_id)
    except Exception as e:
        logger.exception("build_pdf_task failed job=%s", job_id)
        _mark_error(job_id, str(e))
    finally:
        _clear_active(job)
