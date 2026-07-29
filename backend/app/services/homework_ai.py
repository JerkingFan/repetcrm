import asyncio
import logging

from app.config import get_settings, settings
from app.services.homework_output import (
    is_ai_garbage_latex,
    is_degenerate_latex,
    is_latex_document,
    is_repetitive_latex,
    is_valid_latex_homework,
    sanitize_homework_response,
)
from app.services.ollama_client import OllamaError, check_ollama_health, generate_with_ollama
from app.services.openrouter_client import (
    OpenRouterError,
    check_openrouter_health,
    generate_homework_with_openrouter,
    is_configured as openrouter_configured,
)
from app.services.prompts import build_homework_prompt
from app.services.smart_homework import generate_smart_homework_latex

logger = logging.getLogger(__name__)

_local_import_ok = None


def _local_supported() -> bool:
    global _local_import_ok
    if _local_import_ok is None:
        try:
            from app.services.local_llm import local_model_available  # noqa: F401

            _local_import_ok = True
        except Exception:
            _local_import_ok = False
    return _local_import_ok


def _hf_ready() -> bool:
    return settings.local_enable_transformers and _local_supported()


def _settings():
    return get_settings()


def _provider_mode() -> str:
    return (_settings().homework_ai_provider or "smart").strip().lower()


def _use_openrouter() -> bool:
    mode = _provider_mode()
    if mode == "smart":
        return False
    if mode == "openrouter":
        return openrouter_configured()
    return openrouter_configured()


async def get_ai_status() -> dict:
    cfg = _settings()
    openrouter = await check_openrouter_health()
    ollama = await check_ollama_health() if settings.ai_use_ollama else {
        "online": False,
        "model_ready": False,
        "configured_model": settings.ollama_model,
        "models": [],
    }
    from app.services.local_llm import get_local_model_info, resolve_model_dir

    info = get_local_model_info()
    hf_ok = _hf_ready() and info.get("downloaded")
    active = resolve_model_dir()
    model_name = active.split("\\")[-1].split("/")[-1] if active else settings.local_model_id

    provider = (cfg.homework_ai_provider or "smart").strip().lower()
    if provider == "smart" or not openrouter_configured():
        primary = "умный шаблон (стабильные задачи по чек-листу)"
        eta = "Мгновенно"
    elif openrouter_configured() and openrouter.get("online"):
        primary = f"OpenRouter ({cfg.openrouter_model})"
        eta = "OpenRouter: обычно 10–40 сек"
    elif hf_ok and info.get("loaded"):
        primary = f"Hugging Face ({model_name})"
        eta = "Hugging Face: генерация 3–8 мин (модель в памяти)"
    elif hf_ok:
        primary = f"Hugging Face ({model_name})"
        eta = "Hugging Face: ~30 сек загрузка + 3–8 мин"
    else:
        primary = "умный шаблон (без нейросети)"
        eta = "Локальная модель не используется"

    return {
        "openrouter": openrouter,
        "primary_provider": (
            "smart"
            if provider == "smart" or not openrouter_configured()
            else ("openrouter" if openrouter_configured() else ("hf" if hf_ok else "smart"))
        ),
        "homework_ai_provider": provider,
        "ollama": ollama,
        "local_llm": {
            "available": hf_ok,
            "enabled": settings.local_enable_transformers,
            "path": info["dir"],
            "model_file": model_name,
            "downloaded": info.get("downloaded"),
            "loaded": info.get("loaded", False),
            "generating": info.get("generating", False),
            "device": info.get("device", "cpu"),
            "provider": "huggingface",
            "eta_hint": eta,
        },
        "recommended_setup": primary,
        "template_fallback_enabled": settings.ai_allow_template_fallback,
    }


async def generate_homework_ai(
    student_name: str,
    subject: str,
    checklist: list[dict],
    grade: str = "",
    homework_prefs: dict | None = None,
) -> tuple[str, str, str | None]:
    """
    Возвращает (content, source, hint). content — LaTeX-документ.
    source: openrouter | hf | ollama | smart
    """
    from app.services.homework_prefs import apply_prefs_to_checklist, parse_homework_prefs

    cfg = _settings()
    prefs = parse_homework_prefs(homework_prefs)
    checklist = apply_prefs_to_checklist(checklist, prefs, force=True)
    provider_mode = _provider_mode()

    logger.info(
        "generate_homework: provider=%s model=%s openrouter_key=%s",
        provider_mode,
        cfg.openrouter_model,
        bool(cfg.openrouter_api_key.strip()),
    )

    if provider_mode == "openrouter" and not openrouter_configured():
        raise OpenRouterError(
            "В backend/.env задан HOMEWORK_AI_PROVIDER=openrouter, но OPENROUTER_API_KEY пустой"
        )

    # Режим smart — сразу стабильные задачи, без OpenRouter
    if provider_mode == "smart":
        latex = generate_smart_homework_latex(
            student_name, subject, checklist, grade, homework_prefs=prefs
        )
        return latex, "smart", None

    tried_neural = False
    reject_reason = ""

    # 1. OpenRouter (режим openrouter / auto)
    if _use_openrouter():
        tried_neural = True
        try:
            content = await generate_homework_with_openrouter(
                student_name, subject, checklist, grade, prefs
            )
            return content, "openrouter", f"Модель {cfg.openrouter_model}"
        except OpenRouterError:
            raise
        except ValueError as e:
            reject_reason = str(e)
            logger.warning("OpenRouter: LaTeX не принят — fallback (%s)", e)
        except Exception as e:
            reject_reason = f"ошибка запроса: {e}"
            logger.warning("OpenRouter failed: %s", e)

    # 2. Hugging Face (только если OpenRouter выключен и HF включён)
    if _hf_ready() and not _use_openrouter():
        tried_neural = True
        try:
            from app.services.local_llm import (
                generate_with_local_llm,
                local_model_available,
                resolve_model_dir,
            )

            if local_model_available():
                content = await asyncio.wait_for(
                    asyncio.to_thread(
                        generate_with_local_llm,
                        student_name,
                        subject,
                        checklist,
                        grade,
                    ),
                    timeout=settings.local_transformers_timeout_sec,
                )
                if is_valid_latex_homework(content) and not is_degenerate_latex(content):
                    active = resolve_model_dir() or ""
                    name = active.replace("\\", "/").split("/")[-1]
                    return content, "hf", f"Qwen ({name}), LaTeX"
        except asyncio.TimeoutError:
            logger.warning("HF timeout %ss", settings.local_transformers_timeout_sec)
        except Exception as e:
            logger.warning("HF generation failed: %s", e)

    # 3. Ollama
    if settings.ai_use_ollama:
        tried_neural = True
        try:
            raw = await generate_with_ollama(
                build_homework_prompt(student_name, subject, checklist, grade, prefs)
            )
            content = sanitize_homework_response(raw, homework_prefs=prefs)
            if is_valid_latex_homework(content) and not is_degenerate_latex(content):
                return content, "ollama", None
        except OllamaError:
            pass

    # 4. LaTeX по чек-листу
    latex = generate_smart_homework_latex(
        student_name, subject, checklist, grade, homework_prefs=prefs
    )
    hint = None
    source = "smart"
    if tried_neural:
        source = "smart_fallback"
        hint = (
            f"{cfg.openrouter_model}: "
            + (reject_reason or "не удалось получить LaTeX")
            + " — подставлены задачи из чек-листа."
        )
    return latex, source, hint
