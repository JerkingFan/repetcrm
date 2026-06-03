"""Сборка промптов для генерации домашнего задания."""

from app.services.homework_prefs import (
    build_system_prompt_for_homework,
    build_user_prompt_for_homework,
    format_checklist_for_prompt,
)


def format_checklist_items(checklist: list[dict]) -> str:
    return format_checklist_for_prompt(checklist)


def build_homework_prompt(
    student_name: str,
    subject: str,
    checklist: list[dict],
    grade: str = "",
    homework_prefs: dict | None = None,
) -> str:
    return build_user_prompt_for_homework(
        student_name, subject, checklist, grade, homework_prefs
    )


def build_homework_prompt_compact(
    student_name: str,
    subject: str,
    checklist: list[dict],
    grade: str = "",
    homework_prefs: dict | None = None,
) -> str:
    return build_homework_prompt(student_name, subject, checklist, grade, homework_prefs)


def build_homework_system_prompt(homework_prefs: dict | None = None) -> str:
    return build_system_prompt_for_homework(homework_prefs)
