"""Прямая генерация ДЗ через OpenRouter — один запрос, без очередей и fallback."""

from __future__ import annotations

import logging
import re

import httpx

from app.config import get_settings, openrouter_key_hint
from app.services.homework_prefs import (
    format_checklist_for_prompt,
    parse_homework_prefs,
    tasks_per_topic_for_ai,
)
from app.services.html_utils import extract_latex_document, strip_markdown_wrapper
from app.services.openrouter_client import OpenRouterError, _headers

logger = logging.getLogger(__name__)


def build_direct_homework_messages(
    student_name: str,
    subject: str,
    checklist: list[dict],
    grade: str = "",
    homework_prefs: dict | None = None,
) -> list[dict[str, str]]:
    del student_name, grade  # сохраняем сигнатуру API; в промпт не идут
    prefs = parse_homework_prefs(homework_prefs)
    lo, hi = tasks_per_topic_for_ai(prefs, len(checklist))
    topics = format_checklist_for_prompt(checklist)

    system = (
        "Генерируй список заданий в LaTeX.\n"
        "Ответ: только LaTeX от \\documentclass до \\end{document}.\n"
        "Структура: \\section{тема}, затем задачи в \\begin{task}...\\end{task}.\n"
        "Формулы в $...$. Только условия задач, без решений и ответов.\n"
        "Без markdown, без текста вне LaTeX."
    )
    user = (
        f"Предмет: {subject}\n"
        f"Темы:\n{topics}\n\n"
        f"Сделай {lo}–{hi} задач на каждую тему.\n"
        "Выведи полный LaTeX-документ со списком заданий."
    )
    notes = (prefs.get("special_notes") or "").strip()
    if notes:
        user += f"\n\nПожелания: {notes}"

    return [{"role": "system", "content": system}, {"role": "user", "content": user}]


def finalize_openrouter_homework(raw: str) -> str:
    """Минимальная очистка ответа — без отбрасывания «неидеального» LaTeX."""
    text = extract_latex_document(strip_markdown_wrapper(raw))
    if not text.strip():
        raise OpenRouterError("Модель вернула пустой ответ")

    if not re.search(r"\\documentclass", text, re.I):
        raise OpenRouterError("Модель не вернула LaTeX-документ (нет \\documentclass)")

    if not re.search(
        r"\\begin\s*\{\s*task\s*\}|\\item\b",
        text,
        re.I,
    ):
        raise OpenRouterError("В ответе нет задач (\\begin{task} или \\item)")

    if not re.search(r"\\end\s*\{\s*document\s*\}", text, re.I):
        text = text.rstrip() + "\n\\end{document}\n"

    return text.strip()


async def call_openrouter_homework(messages: list[dict]) -> str:
    """Один HTTP POST в OpenRouter. Без circuit breaker, без retry."""
    cfg = get_settings()
    if not cfg.openrouter_api_key.strip():
        raise OpenRouterError("OPENROUTER_API_KEY не задан в backend/.env")

    payload = {
        "model": cfg.openrouter_model,
        "messages": messages,
        "temperature": 0.3,
        "max_tokens": min(3500, cfg.openrouter_max_tokens),
    }
    url = f"{cfg.openrouter_base_url.rstrip('/')}/chat/completions"
    timeout = min(90.0, cfg.openrouter_timeout_sec)

    logger.info("OpenRouter homework: model=%s, timeout=%ss", cfg.openrouter_model, timeout)

    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(url, headers=_headers(), json=payload)
    except httpx.TimeoutException as exc:
        raise OpenRouterError("Таймаут OpenRouter — попробуйте ещё раз") from exc
    except httpx.HTTPError as exc:
        raise OpenRouterError(f"Ошибка сети OpenRouter: {exc}") from exc

    if response.status_code == 401:
        raise OpenRouterError(
            f"Неверный OPENROUTER_API_KEY ({openrouter_key_hint(cfg.openrouter_api_key)})"
        )
    if response.status_code == 402:
        raise OpenRouterError("Недостаточно средств на OpenRouter")
    if not response.is_success:
        detail = response.text[:300]
        raise OpenRouterError(f"OpenRouter HTTP {response.status_code}: {detail}")

    data = response.json()
    choices = data.get("choices") or []
    if not choices:
        raise OpenRouterError("Пустой ответ OpenRouter")

    raw = (choices[0].get("message") or {}).get("content") or ""
    if not raw.strip():
        raise OpenRouterError("Пустой текст от OpenRouter")

    logger.info("OpenRouter homework: received %s chars", len(raw))
    return raw


async def generate_homework_direct(
    student_name: str,
    subject: str,
    checklist: list[dict],
    grade: str = "",
    homework_prefs: dict | None = None,
) -> str:
    """Прямой путь: промпт → OpenRouter → LaTeX. Один запрос."""
    messages = build_direct_homework_messages(
        student_name, subject, checklist, grade, homework_prefs
    )
    raw = await call_openrouter_homework(messages)
    return finalize_openrouter_homework(raw)
