"""Быстрая офлайн-модель через llama-cpp + GGUF (~500 МБ)."""

import logging
import os
import threading
from pathlib import Path

from app.config import settings
from app.services.homework_output import sanitize_homework_response
from app.services.prompts import build_homework_prompt

logger = logging.getLogger(__name__)

_llm = None
_lock = threading.Lock()
_fast_disabled = False
_fast_disable_reason: str | None = None

SYSTEM = (
    "Генератор LaTeX. Ответ — только LaTeX code от \\documentclass до \\end{document}. "
    "Без markdown и без текста вне документа."
)


def fast_model_file_exists() -> bool:
    p = Path(settings.local_fast_gguf_path)
    return p.is_file() and p.stat().st_size > 50_000_000


def fast_model_usable() -> bool:
    """Файл есть и llama-cpp реально запускается на этом CPU."""
    return fast_model_file_exists() and not _fast_disabled


def get_fast_status() -> dict:
    return {
        "file_exists": fast_model_file_exists(),
        "usable": fast_model_usable(),
        "disabled_reason": _fast_disable_reason,
    }


def _mark_fast_broken(exc: Exception) -> None:
    global _fast_disabled, _fast_disable_reason
    _fast_disabled = True
    _fast_disable_reason = str(exc)
    logger.warning("Быстрая GGUF отключена на этом ПК: %s", exc)


def _get_llm():
    global _llm
    if _fast_disabled:
        raise RuntimeError(_fast_disable_reason or "Быстрая модель недоступна на этом CPU")
    if _llm is not None:
        return _llm
    with _lock:
        if _llm is not None:
            return _llm
        try:
            from llama_cpp import Llama
        except ImportError as e:
            _mark_fast_broken(e)
            raise
        if not fast_model_file_exists():
            raise RuntimeError(
                f"Файл не найден: {settings.local_fast_gguf_path}. "
                "Запустите: python scripts/download_fast_model.py"
            )
        try:
            _llm = Llama(
                model_path=settings.local_fast_gguf_path,
                n_ctx=2048,
                n_threads=max(4, (os.cpu_count() or 4)),
                verbose=False,
            )
        except OSError as e:
            # 0xc000001d — несовместимость AVX/инструкций CPU на Windows
            _mark_fast_broken(e)
            raise
        return _llm


def generate_with_fast_local(
    student_name: str,
    subject: str,
    checklist: list[dict],
    grade: str = "",
) -> str:
    llm = _get_llm()
    user = build_homework_prompt(student_name, subject, checklist, grade)
    out = llm.create_chat_completion(
        messages=[
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": user},
        ],
        temperature=0.4,
        max_tokens=settings.local_fast_max_tokens,
    )
    raw = out["choices"][0]["message"]["content"]
    if not raw or not raw.strip():
        raise RuntimeError("Пустой ответ быстрой модели")
    try:
        return sanitize_homework_response(raw)
    except ValueError:
        return raw.strip() if raw.strip().startswith("<") else f"<div>{raw}</div>"


def preload_fast_background() -> None:
    def _run():
        if not fast_model_file_exists():
            return
        try:
            _get_llm()
            logger.info("Быстрая GGUF-модель загружена")
        except Exception as e:
            logger.warning("Предзагрузка быстрой модели: %s", e)

    threading.Thread(target=_run, daemon=True, name="fast-llm-preload").start()
