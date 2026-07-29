"""Генерация домашки через OpenRouter (OpenAI-совместимый API)."""

import asyncio
import logging
import random

import httpx

from app.config import get_settings, openrouter_key_hint
from app.services.circuit_breaker import CircuitBreaker, CircuitOpenError
from app.services.homework_output import accept_openrouter_latex, coerce_openrouter_latex
from app.services.homework_prefs import parse_homework_prefs
from app.services.prompts import build_homework_prompt, build_homework_system_prompt

logger = logging.getLogger(__name__)

_openrouter_circuit = CircuitBreaker(
    "openrouter",
    failure_threshold=get_settings().openrouter_circuit_failures,
    reset_timeout_sec=get_settings().openrouter_circuit_reset_sec,
)

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


async def _call_openrouter(
    messages: list[dict],
    *,
    max_tokens: int | None = None,
    timeout_sec: float | None = None,
) -> str:
    cfg = get_settings()
    try:
        _openrouter_circuit.before_call()
    except CircuitOpenError as exc:
        raise OpenRouterError("OpenRouter временно недоступен (circuit open)") from exc

    token_cap = max_tokens if max_tokens is not None else min(2000, cfg.openrouter_max_tokens)
    req_timeout = timeout_sec if timeout_sec is not None else min(90.0, cfg.openrouter_timeout_sec)

    payload = {
        "model": cfg.openrouter_model,
        "messages": messages,
        "temperature": 0.25,
        "max_tokens": token_cap,
        "provider": {"allow_fallbacks": True},
    }
    url = f"{cfg.openrouter_base_url.rstrip('/')}/chat/completions"
    max_retries = max(1, cfg.openrouter_max_retries)
    last_error: Exception | None = None

    for attempt in range(max_retries):
        try:
            async with httpx.AsyncClient(timeout=req_timeout) as client:
                response = await client.post(url, headers=_headers(), json=payload)
                if response.status_code == 401:
                    raise OpenRouterError(
                        "Неверный OPENROUTER_API_KEY "
                        f"({openrouter_key_hint(cfg.openrouter_api_key)}). "
                        "Проверьте backend/.env: один ключ, без дубликатов, перезапустите API и worker"
                    )
                if response.status_code == 402:
                    raise OpenRouterError("Недостаточно средств на OpenRouter")
                if response.status_code in (429, 502, 503, 504):
                    if attempt < max_retries - 1:
                        delay = min(30.0, (2**attempt) + random.uniform(0, 0.5))
                        logger.warning(
                            "OpenRouter HTTP %s, retry %s/%s in %.1fs",
                            response.status_code,
                            attempt + 1,
                            max_retries,
                            delay,
                        )
                        await asyncio.sleep(delay)
                        continue
                    raise OpenRouterError(
                        f"OpenRouter перегружен (HTTP {response.status_code}). Попробуйте позже."
                    )
                response.raise_for_status()
                data = response.json()
            choices = data.get("choices") or []
            if not choices:
                raise OpenRouterError("Пустой ответ OpenRouter")
            raw = (choices[0].get("message") or {}).get("content") or ""
            if not raw.strip():
                raise OpenRouterError("Пустой текст от OpenRouter")
            _openrouter_circuit.record_success()
            return raw
        except OpenRouterError:
            _openrouter_circuit.record_failure()
            raise
        except httpx.TimeoutException as e:
            last_error = e
            if attempt < max_retries - 1:
                await asyncio.sleep((2**attempt) + random.uniform(0, 0.3))
                continue
            raise OpenRouterError("Таймаут OpenRouter — попробуйте ещё раз") from e
        except httpx.HTTPStatusError as e:
            last_error = e
            if attempt < max_retries - 1 and e.response is not None and e.response.status_code >= 500:
                await asyncio.sleep((2**attempt) + random.uniform(0, 0.3))
                continue
            detail = e.response.text[:300] if e.response else str(e)
            raise OpenRouterError(f"OpenRouter HTTP {e.response.status_code}: {detail}") from e
        except httpx.HTTPError as e:
            last_error = e
            if attempt < max_retries - 1:
                await asyncio.sleep((2**attempt) + random.uniform(0, 0.3))
                continue
            raise OpenRouterError(f"Ошибка сети OpenRouter: {e}") from e

    _openrouter_circuit.record_failure()
    raise OpenRouterError(f"OpenRouter недоступен: {last_error}")


async def call_openrouter_vision(
    *,
    system_prompt: str,
    user_prompt: str,
    image_data_url: str,
    model: str | None = None,
) -> str:
    """Vision completion via OpenRouter (multimodal messages)."""
    cfg = get_settings()
    if not is_configured():
        raise OpenRouterError("OPENROUTER_API_KEY не задан в backend/.env")

    vision_model = (model or cfg.openrouter_vision_model or cfg.openrouter_model).strip()
    messages = [
        {"role": "system", "content": system_prompt},
        {
            "role": "user",
            "content": [
                {"type": "text", "text": user_prompt},
                {"type": "image_url", "image_url": {"url": image_data_url}},
            ],
        },
    ]

    try:
        _openrouter_circuit.before_call()
    except CircuitOpenError as exc:
        raise OpenRouterError("OpenRouter временно недоступен (circuit open)") from exc

    payload = {
        "model": vision_model,
        "messages": messages,
        "temperature": 0.2,
        "max_tokens": min(2048, cfg.openrouter_max_tokens),
    }
    url = f"{cfg.openrouter_base_url.rstrip('/')}/chat/completions"
    max_retries = max(1, cfg.openrouter_max_retries)
    last_error: Exception | None = None

    for attempt in range(max_retries):
        try:
            async with httpx.AsyncClient(timeout=cfg.openrouter_timeout_sec) as client:
                response = await client.post(url, headers=_headers(), json=payload)
                if response.status_code == 401:
                    raise OpenRouterError(
                        "Неверный OPENROUTER_API_KEY "
                        f"({openrouter_key_hint(cfg.openrouter_api_key)}). "
                        "Проверьте backend/.env: один ключ, без дубликатов, перезапустите API и worker"
                    )
                if response.status_code == 402:
                    raise OpenRouterError("Недостаточно средств на OpenRouter")
                if response.status_code in (429, 502, 503, 504):
                    if attempt < max_retries - 1:
                        delay = min(30.0, (2**attempt) + random.uniform(0, 0.5))
                        await asyncio.sleep(delay)
                        continue
                    raise OpenRouterError(
                        f"OpenRouter перегружен (HTTP {response.status_code}). Попробуйте позже."
                    )
                response.raise_for_status()
                data = response.json()
            choices = data.get("choices") or []
            if not choices:
                raise OpenRouterError("Пустой ответ OpenRouter")
            raw = (choices[0].get("message") or {}).get("content") or ""
            if not raw.strip():
                raise OpenRouterError("Пустой текст от OpenRouter")
            _openrouter_circuit.record_success()
            return raw
        except OpenRouterError:
            _openrouter_circuit.record_failure()
            raise
        except httpx.TimeoutException as e:
            last_error = e
            if attempt < max_retries - 1:
                await asyncio.sleep((2**attempt) + random.uniform(0, 0.3))
                continue
            raise OpenRouterError("Таймаут OpenRouter — попробуйте ещё раз") from e
        except httpx.HTTPStatusError as e:
            last_error = e
            if attempt < max_retries - 1 and e.response is not None and e.response.status_code >= 500:
                await asyncio.sleep((2**attempt) + random.uniform(0, 0.3))
                continue
            detail = e.response.text[:300] if e.response else str(e)
            raise OpenRouterError(f"OpenRouter HTTP {e.response.status_code}: {detail}") from e
        except httpx.HTTPError as e:
            last_error = e
            if attempt < max_retries - 1:
                await asyncio.sleep((2**attempt) + random.uniform(0, 0.3))
                continue
            raise OpenRouterError(f"Ошибка сети OpenRouter: {e}") from e

    _openrouter_circuit.record_failure()
    raise OpenRouterError(f"OpenRouter недоступен: {last_error}")


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
    topic_count = len(checklist)
    system_prompt = build_homework_system_prompt(prefs, topic_count=topic_count)
    user_prompt = build_homework_prompt(
        student_name, subject, checklist, grade, prefs
    )
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]

    try:
        raw = await _call_openrouter(messages, max_tokens=2000, timeout_sec=75.0)
        logger.info(
            "OpenRouter: %s chars, model %s, topics=%s",
            len(raw),
            cfg.openrouter_model,
            topic_count,
        )
        try:
            return coerce_openrouter_latex(raw, homework_prefs=prefs)
        except ValueError as first_err:
            logger.info("OpenRouter pass1 coerce: %s", first_err)

        content, issues = accept_openrouter_latex(raw, homework_prefs=prefs)
        if content:
            logger.info("OpenRouter pass1 lenient accept (%s)", ", ".join(issues) or "ok")
            return content

        fix_user = (
            "Ответ не в формате LaTeX. Выведи ЗАНОВО ТОЛЬКО LaTeX code: "
            "с \\documentclass до \\end{document}. Без markdown. "
            "Каждый \\begin{task} — полное условие с формулами $...$."
        )
        messages.append({"role": "assistant", "content": raw[:4000]})
        messages.append({"role": "user", "content": fix_user})
        raw2 = await _call_openrouter(messages, max_tokens=2000, timeout_sec=75.0)
        logger.info("OpenRouter retry: %s chars", len(raw2))
        return coerce_openrouter_latex(raw2, homework_prefs=prefs)
    except httpx.TimeoutException as e:
        raise OpenRouterError("Таймаут OpenRouter — попробуйте ещё раз") from e
    except httpx.HTTPStatusError as e:
        detail = e.response.text[:300] if e.response else str(e)
        raise OpenRouterError(f"OpenRouter HTTP {e.response.status_code}: {detail}") from e
    except httpx.HTTPError as e:
        raise OpenRouterError(f"Ошибка сети OpenRouter: {e}") from e
