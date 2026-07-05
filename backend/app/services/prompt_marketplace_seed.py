"""Seed official prompt marketplace catalog."""

from __future__ import annotations

import json

from sqlalchemy.orm import Session

from app.models import PromptTemplate
from app.services.homework_prefs import DEFAULT_HOMEWORK_PREFS, serialize_homework_prefs

_CATALOG = [
    {
        "title": "Математика 5 класс — дроби",
        "description": "Практика на сложение и сравнение обыкновенных дробей",
        "subject": "Математика",
        "grade": "5",
        "checklist": [{"topic": "Обыкновенные дроби", "work_type": "practice", "difficulty": "medium", "understanding": 3}],
        "prefs": {"focus_aspect": "practice", "volume": "standard", "difficulty_level": "medium"},
    },
    {
        "title": "Математика 8 класс — уравнения",
        "description": "Линейные уравнения с одной переменной",
        "subject": "Математика",
        "grade": "8",
        "checklist": [{"topic": "Линейные уравнения", "work_type": "practice", "difficulty": "medium", "understanding": 3}],
        "prefs": {"focus_aspect": "practice", "volume": "standard", "task_types": ["practice_rules", "text_problems"]},
    },
    {
        "title": "Математика 9 класс — квадратные уравнения",
        "description": "Решение квадратных уравнений и дискриминант",
        "subject": "Математика",
        "grade": "9",
        "checklist": [{"topic": "Квадратные уравнения", "work_type": "practice", "difficulty": "advanced", "understanding": 3}],
        "prefs": {"focus_aspect": "mixed", "volume": "extended", "difficulty_level": "high"},
    },
    {
        "title": "Физика 9 класс — механика",
        "description": "Задачи на скорость, ускорение, силу",
        "subject": "Физика",
        "grade": "9",
        "checklist": [{"topic": "Равномерное движение", "work_type": "practice", "difficulty": "medium", "understanding": 3}],
        "prefs": {"focus_aspect": "practice", "task_types": ["text_problems"], "volume": "standard"},
    },
    {
        "title": "Русский язык 6 класс — орфография",
        "description": "Правописание безударных гласных и приставок",
        "subject": "Русский язык",
        "grade": "6",
        "checklist": [{"topic": "Орфография", "work_type": "practice", "difficulty": "basic", "understanding": 3}],
        "prefs": {"focus_aspect": "practice", "volume": "minimal", "include_hints": True},
    },
    {
        "title": "Английский 7 класс — Present Simple",
        "description": "Упражнения на времена и перевод",
        "subject": "Английский язык",
        "grade": "7",
        "checklist": [{"topic": "Present Simple", "work_type": "practice", "difficulty": "medium", "understanding": 3}],
        "prefs": {"focus_aspect": "mixed", "task_types": ["translation", "practice_rules"], "volume": "standard"},
    },
    {
        "title": "Химия 10 класс — стехиометрия",
        "description": "Расчёты по уравнениям реакций",
        "subject": "Химия",
        "grade": "10",
        "checklist": [{"topic": "Стехиометрия", "work_type": "practice", "difficulty": "advanced", "understanding": 4}],
        "prefs": {"focus_aspect": "practice", "volume": "extended", "difficulty_level": "high"},
    },
    {
        "title": "Математика 11 класс — подготовка к ЦТ",
        "description": "Смешанные задания повышенной сложности",
        "subject": "Математика",
        "grade": "11",
        "checklist": [
            {"topic": "Производная", "work_type": "test", "difficulty": "advanced", "understanding": 4},
            {"topic": "Интегралы", "work_type": "test", "difficulty": "advanced", "understanding": 3},
        ],
        "prefs": {"focus_aspect": "mixed", "student_level": "exam", "volume": "extended", "difficulty_level": "high"},
    },
]


def ensure_prompt_catalog_seeded(db: Session) -> int:
    from sqlalchemy import inspect

    if not inspect(db.bind).has_table("prompt_templates"):
        return 0
    existing = db.query(PromptTemplate).filter(PromptTemplate.author_user_id.is_(None)).count()
    if existing >= len(_CATALOG):
        return 0
    added = 0
    for item in _CATALOG:
        dup = (
            db.query(PromptTemplate)
            .filter(
                PromptTemplate.author_user_id.is_(None),
                PromptTemplate.title == item["title"],
            )
            .first()
        )
        if dup:
            continue
        prefs = {**DEFAULT_HOMEWORK_PREFS, **item.get("prefs", {})}
        db.add(
            PromptTemplate(
                author_user_id=None,
                title=item["title"],
                description=item["description"],
                subject=item["subject"],
                grade=item["grade"],
                homework_prefs=serialize_homework_prefs(prefs),
                checklist_json=json.dumps(item["checklist"], ensure_ascii=False),
                visibility="public",
            )
        )
        added += 1
    if added:
        db.commit()
    return added
