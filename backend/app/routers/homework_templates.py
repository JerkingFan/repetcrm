"""Saved homework templates — reuse successful generations."""

from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models import ChecklistItem, Homework, HomeworkTemplate, Lesson, User
from app.routers.lessons import get_lesson_or_404, lesson_to_out
from app.schemas import (
    ApplyHomeworkTemplateIn,
    HomeworkTemplateCreate,
    HomeworkTemplateFromLessonIn,
    HomeworkTemplateOut,
    HomeworkTemplateUpdate,
    LessonOut,
)
from app.services.homework_prefs import parse_homework_prefs, serialize_homework_prefs
from app.services.pdf import invalidate_homework_pdf

router = APIRouter(prefix="/homework-templates", tags=["homework-templates"])


def _preview(text: str) -> str:
    clean = " ".join((text or "").split())
    return clean[:200] + ("…" if len(clean) > 200 else "")


def _checklist_from_json(raw: str) -> list[dict]:
    try:
        data = json.loads(raw or "[]")
    except json.JSONDecodeError:
        return []
    if not isinstance(data, list):
        return []
    return [item for item in data if isinstance(item, dict)]


def _template_to_out(t: HomeworkTemplate) -> HomeworkTemplateOut:
    prefs = parse_homework_prefs(t.homework_prefs)
    checklist_items = [
        {
            "id": 0,
            "lesson_id": 0,
            "topic": item.get("topic", ""),
            "work_type": item.get("work_type", "practice"),
            "difficulty": item.get("difficulty", "medium"),
            "understanding": int(item.get("understanding", 3) or 3),
        }
        for item in _checklist_from_json(t.checklist_json)
    ]
    return HomeworkTemplateOut(
        id=t.id,
        name=t.name,
        subject=t.subject,
        homework_text=t.homework_text,
        homework_prefs=prefs,
        checklist_items=checklist_items,
        source_lesson_id=t.source_lesson_id,
        preview=_preview(t.homework_text),
        created_at=t.created_at,
        updated_at=t.updated_at,
    )


def get_template_or_404(template_id: int, user: User, db: Session) -> HomeworkTemplate:
    t = (
        db.query(HomeworkTemplate)
        .filter(HomeworkTemplate.id == template_id, HomeworkTemplate.tutor_id == user.id)
        .first()
    )
    if not t:
        raise HTTPException(status_code=404, detail="Template not found")
    return t


@router.get("", response_model=list[HomeworkTemplateOut])
def list_templates(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    rows = (
        db.query(HomeworkTemplate)
        .filter(HomeworkTemplate.tutor_id == user.id)
        .order_by(HomeworkTemplate.updated_at.desc())
        .all()
    )
    return [_template_to_out(t) for t in rows]


@router.post("", response_model=HomeworkTemplateOut, status_code=201)
def create_template(
    data: HomeworkTemplateCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    t = HomeworkTemplate(
        tutor_id=user.id,
        name=data.name.strip(),
        subject=data.subject.strip(),
        homework_text=data.homework_text,
        homework_prefs=serialize_homework_prefs(data.homework_prefs.model_dump()),
        checklist_json=json.dumps([item.model_dump() for item in data.checklist_items], ensure_ascii=False),
    )
    db.add(t)
    db.commit()
    db.refresh(t)
    return _template_to_out(t)


@router.post("/from-lesson/{lesson_id}", response_model=HomeworkTemplateOut, status_code=201)
def create_template_from_lesson(
    lesson_id: int,
    data: HomeworkTemplateFromLessonIn,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    lesson = get_lesson_or_404(lesson_id, user, db)
    checklist = [
        {
            "topic": i.topic,
            "work_type": i.work_type,
            "difficulty": i.difficulty,
            "understanding": i.understanding,
        }
        for i in lesson.checklist_items
    ]
    if not checklist and not (data.include_homework_text and lesson.homework and lesson.homework.homework_text.strip()):
        raise HTTPException(status_code=400, detail="Нет чек-листа и текста ДЗ для сохранения")

    hw_text = ""
    if data.include_homework_text and lesson.homework:
        hw_text = lesson.homework.homework_text or ""

    t = HomeworkTemplate(
        tutor_id=user.id,
        name=data.name.strip(),
        subject=lesson.student.subject if lesson.student else "",
        homework_text=hw_text,
        homework_prefs=lesson.homework_prefs or "",
        checklist_json=json.dumps(checklist, ensure_ascii=False),
        source_lesson_id=lesson.id,
    )
    db.add(t)
    db.commit()
    db.refresh(t)
    return _template_to_out(t)


@router.get("/{template_id}", response_model=HomeworkTemplateOut)
def get_template(
    template_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    return _template_to_out(get_template_or_404(template_id, user, db))


@router.put("/{template_id}", response_model=HomeworkTemplateOut)
def update_template(
    template_id: int,
    data: HomeworkTemplateUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    t = get_template_or_404(template_id, user, db)
    updates = data.model_dump(exclude_unset=True)
    if "name" in updates and updates["name"]:
        t.name = updates["name"].strip()
    if "subject" in updates and updates["subject"] is not None:
        t.subject = updates["subject"].strip()
    if "homework_text" in updates and updates["homework_text"] is not None:
        t.homework_text = updates["homework_text"]
    if "homework_prefs" in updates and updates["homework_prefs"] is not None:
        t.homework_prefs = serialize_homework_prefs(updates["homework_prefs"].model_dump())
    if "checklist_items" in updates and updates["checklist_items"] is not None:
        t.checklist_json = json.dumps(
            [item.model_dump() for item in updates["checklist_items"]], ensure_ascii=False
        )
    db.commit()
    db.refresh(t)
    return _template_to_out(t)


@router.delete("/{template_id}", status_code=204)
def delete_template(
    template_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    t = get_template_or_404(template_id, user, db)
    db.delete(t)
    db.commit()


@router.post("/{template_id}/apply-to-lesson/{lesson_id}", response_model=LessonOut)
def apply_template_to_lesson(
    template_id: int,
    lesson_id: int,
    data: ApplyHomeworkTemplateIn,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    t = get_template_or_404(template_id, user, db)
    lesson = get_lesson_or_404(lesson_id, user, db)

    db.query(ChecklistItem).filter(ChecklistItem.lesson_id == lesson_id).delete()
    for item in _checklist_from_json(t.checklist_json):
        topic = (item.get("topic") or "").strip()
        if not topic:
            continue
        db.add(
            ChecklistItem(
                lesson_id=lesson_id,
                topic=topic,
                work_type=item.get("work_type", "practice"),
                difficulty=item.get("difficulty", "medium"),
                understanding=int(item.get("understanding", 3) or 3),
            )
        )

    if t.homework_prefs:
        lesson.homework_prefs = t.homework_prefs

    if data.copy_homework_text and t.homework_text.strip():
        if lesson.homework:
            lesson.homework.homework_text = t.homework_text
            invalidate_homework_pdf(lesson.homework.id)
        else:
            hw = Homework(lesson_id=lesson_id, homework_text=t.homework_text)
            db.add(hw)

    db.commit()
    lesson = get_lesson_or_404(lesson_id, user, db)
    return lesson_to_out(lesson)
