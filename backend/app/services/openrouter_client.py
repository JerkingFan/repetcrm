"""Генерация домашки через OpenRouter (OpenAI-совместимый API)."""

import logging

import httpx

from app.config import get_settings
from app.services.homework_output import coerce_openrouter_latex
from app.services.homework_prefs import parse_homework_prefs
from app.services.prompts import build_homework_prompt, build_homework_system_prompt

logger = logging.getLogger(__name__)



class OpenRouterError(Exception):
    pass


def is_configured() -> bool:
    return bool(get_settings().openrouter_api_key.strip())


async def check_openrouter_health() -> dict:
    if not is_configured():
        return {
            "configured": False,
            "online": False,
            "model": get_settings().openrouter_model,
        }
    cfg = get_settings()
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            r = await client.get(
                f"{cfg.openrouter_base_url.rstrip('/')}/models",
                headers=_headers(),
            )
            r.raise_for_status()
            return {
                "configured": True,
                "online": True,
                "model": cfg.openrouter_model,
            }
    except Exception as e:
        return {
            "configured": True,
            "online": False,
            "model": cfg.openrouter_model,
            "error": str(e),
        }


def _headers() -> dict[str, str]:
    cfg = get_settings()
    return {
        "Authorization": f"Bearer {cfg.openrouter_api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": cfg.openrouter_site_url,
        "X-Title": cfg.openrouter_app_name,
    }


async def _call_openrouter(messages: list[dict]) -> str:
    cfg = get_settings()
    payload = {
        "model": cfg.openrouter_model,
        "messages": messages,
        "temperature": 0.25,
        "max_tokens": cfg.openrouter_max_tokens,
    }
    url = f"{cfg.openrouter_base_url.rstrip('/')}/chat/completions"
    async with httpx.AsyncClient(timeout=cfg.openrouter_timeout_sec) as client:
        response = await client.post(url, headers=_headers(), json=payload)
        if response.status_code == 401:
            raise OpenRouterError("Неверный OPENROUTER_API_KEY")
        if response.status_code == 402:
            raise OpenRouterError("Недостаточно средств на OpenRouter")
        response.raise_for_status()
        data = response.json()
    choices = data.get("choices") or []
    if not choices:
        raise OpenRouterError("Пустой ответ OpenRouter")
    raw = (choices[0].get("message") or {}).get("content") or ""
    if not raw.strip():
        raise OpenRouterError("Пустой текст от OpenRouter")
    return raw


async def generate_homework_with_openrouter(
    student_name: str,
    subject: str,
    checklist: list[dict],
    grade: str = "",
    homework_prefs: dict | None = None,
) -> str:
    if not is_configured():
        raise OpenRouterError("OPENROUTER_API_KEY не задан в backend/.env")

    cfg = get_settings()
    prefs = parse_homework_prefs(homework_prefs)
    system_prompt = build_homework_system_prompt(prefs)
    user_prompt = build_homework_prompt(
        student_name, subject, checklist, grade, prefs
    )
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]

    try:
        raw = await _call_openrouter(messages)
        logger.info(
            "OpenRouter: %s chars, model %s",
            len(raw),
            cfg.openrouter_model,
        )
        try:
            return coerce_openrouter_latex(raw, homework_prefs=prefs)
        except ValueError as first_err:
            logger.info("OpenRouter pass1 coerce: %s", first_err)

        fix_user = (
            "Ответ не в формате LaTeX. Выведи ЗАНОВО ТОЛЬКО LaTeX code: "
            "с \\documentclass до \\end{document}. Без markdown. "
            "Каждый \\begin{task} — полное условие с формулами $...$."
        )
        messages.append({"role": "assistant", "content": raw[:4000]})
        messages.append({"role": "user", "content": fix_user})
        raw2 = await _call_openrouter(messages)
        logger.info("OpenRouter retry: %s chars", len(raw2))
        return coerce_openrouter_latex(raw2, homework_prefs=prefs)
    except httpx.TimeoutException as e:
        raise OpenRouterError("Таймаут OpenRouter — попробуйте ещё раз") from e
    except httpx.HTTPStatusError as e:
        detail = e.response.text[:300] if e.response else str(e)
        raise OpenRouterError(f"OpenRouter HTTP {e.response.status_code}: {detail}") from e
    except httpx.HTTPError as e:
        raise OpenRouterError(f"Ошибка сети OpenRouter: {e}") from e
