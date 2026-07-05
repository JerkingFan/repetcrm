"""Public prompt marketplace by subject and grade."""

from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models import HomeworkTemplate, PromptTemplate, PromptTemplateInstall, User
from app.schemas import ChecklistItemOut, HomeworkPrefs, PromptTemplateInstallOut, PromptTemplateOut
from app.services.homework_prefs import parse_homework_prefs

router = APIRouter(prefix="/prompt-templates", tags=["prompt-marketplace"])


def _checklist_from_json(raw: str) -> list[dict]:
    try:
        data = json.loads(raw or "[]")
    except json.JSONDecodeError:
        return []
    return [x for x in data if isinstance(x, dict)]


def _to_out(t: PromptTemplate, installed: bool) -> PromptTemplateOut:
    prefs = parse_homework_prefs(t.homework_prefs)
    items = [
        ChecklistItemOut(
            id=0,
            lesson_id=0,
            topic=item.get("topic", ""),
            work_type=item.get("work_type", "practice"),
            difficulty=item.get("difficulty", "medium"),
            understanding=int(item.get("understanding", 3) or 3),
        )
        for item in _checklist_from_json(t.checklist_json)
    ]
    return PromptTemplateOut(
        id=t.id,
        title=t.title,
        description=t.description,
        subject=t.subject,
        grade=t.grade,
        homework_prefs=HomeworkPrefs(**prefs),
        checklist_items=items,
        use_count=t.use_count,
        installed=installed,
        created_at=t.created_at,
    )


@router.get("", response_model=list[PromptTemplateOut])
def list_prompt_templates(
    subject: str | None = Query(None),
    grade: str | None = Query(None),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    q = db.query(PromptTemplate).filter(PromptTemplate.visibility == "public")
    if subject:
        q = q.filter(PromptTemplate.subject.ilike(f"%{subject.strip()}%"))
    if grade:
        q = q.filter(PromptTemplate.grade == grade.strip())
    rows = q.order_by(PromptTemplate.use_count.desc(), PromptTemplate.title.asc()).all()

    installed_ids = {
        row[0]
        for row in db.query(PromptTemplateInstall.template_id)
        .filter(PromptTemplateInstall.tutor_id == user.id)
        .all()
    }
    return [_to_out(t, t.id in installed_ids) for t in rows]


@router.get("/{template_id}", response_model=PromptTemplateOut)
def get_prompt_template(
    template_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    t = db.query(PromptTemplate).filter(PromptTemplate.id == template_id).first()
    if not t or t.visibility != "public":
        raise HTTPException(status_code=404, detail="Not found")
    installed = (
        db.query(PromptTemplateInstall)
        .filter(
            PromptTemplateInstall.tutor_id == user.id,
            PromptTemplateInstall.template_id == template_id,
        )
        .first()
        is not None
    )
    return _to_out(t, installed)


@router.post("/{template_id}/install", response_model=PromptTemplateInstallOut)
def install_prompt_template(
    template_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    t = db.query(PromptTemplate).filter(PromptTemplate.id == template_id).first()
    if not t or t.visibility != "public":
        raise HTTPException(status_code=404, detail="Not found")

    existing = (
        db.query(PromptTemplateInstall)
        .filter(
            PromptTemplateInstall.tutor_id == user.id,
            PromptTemplateInstall.template_id == template_id,
        )
        .first()
    )
    if existing and existing.homework_template_id:
        return PromptTemplateInstallOut(
            template_id=template_id,
            homework_template_id=existing.homework_template_id,
            message="Уже установлено",
        )

    hw_tpl = HomeworkTemplate(
        tutor_id=user.id,
        name=t.title,
        subject=t.subject,
        homework_text=t.sample_homework_text or "",
        homework_prefs=t.homework_prefs,
        checklist_json=t.checklist_json,
    )
    db.add(hw_tpl)
    db.flush()

    if existing:
        existing.homework_template_id = hw_tpl.id
    else:
        db.add(
            PromptTemplateInstall(
                tutor_id=user.id,
                template_id=template_id,
                homework_template_id=hw_tpl.id,
            )
        )
    t.use_count += 1
    db.commit()

    return PromptTemplateInstallOut(
        template_id=template_id,
        homework_template_id=hw_tpl.id,
        message="Промпт добавлен в «Мои шаблоны»",
    )
