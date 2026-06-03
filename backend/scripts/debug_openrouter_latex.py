#!/usr/bin/env python3
"""Диагностика: почему LaTeX от OpenRouter не принимается."""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.services.html_utils import extract_latex_document
from app.services.homework_output import (
    accept_openrouter_latex,
    is_latex_document,
    latex_validation_issues,
    _extract_task_bodies,
    repair_ai_latex_document,
)
from app.services.homework_prefs import DEFAULT_HOMEWORK_PREFS, parse_homework_prefs


async def main():
    from app.services.openrouter_client import _call_openrouter
    from app.services.prompts import build_homework_prompt, build_homework_system_prompt

    prefs = parse_homework_prefs(DEFAULT_HOMEWORK_PREFS)
    checklist = [
        {
            "topic": "Тригонометрические неравенства",
            "work_type": "practice",
            "difficulty": "medium",
            "understanding": 3,
        }
    ]
    messages = [
        {"role": "system", "content": build_homework_system_prompt(prefs)},
        {
            "role": "user",
            "content": build_homework_prompt("Тест", "Математика", checklist, "9", prefs),
        },
    ]
    print("Calling OpenRouter...")
    raw = await _call_openrouter(messages)
    print(f"Raw length: {len(raw)}")
    print(f"First 200 chars: {raw[:200]!r}")
    extracted = extract_latex_document(raw)
    print(f"is_latex_document(extracted): {is_latex_document(extracted)}")
    print(f"tasks in extracted: {len(_extract_task_bodies(extracted))}")
    print(f"issues extracted: {latex_validation_issues(extracted)}")
    repaired = repair_ai_latex_document(raw, prefs)
    print(f"repair: {repaired is not None}, tasks={len(_extract_task_bodies(repaired or ''))}")
    content, issues = accept_openrouter_latex(raw, prefs)
    print(f"accept: {content is not None}")
    print(f"issues: {issues}")
    if not content:
        print("SAMPLE tasks:", _extract_task_bodies(extracted)[:3])


if __name__ == "__main__":
    asyncio.run(main())
