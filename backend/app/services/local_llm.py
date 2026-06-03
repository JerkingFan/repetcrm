"""Встроенная модель Qwen2.5 через transformers (офлайн, без Ollama)."""

import logging
import os
import threading
import time
from pathlib import Path

from app.config import settings
from app.services.homework_output import sanitize_homework_response
from app.services.prompts import build_homework_prompt

logger = logging.getLogger(__name__)

# От умнее к быстрее (если целевая папка из config пуста)
MODEL_DIR_CANDIDATES = (
    "./models/Qwen2.5-1.5B-Instruct",
    "./models/Qwen2.5-3B-Instruct",
    "./models/Qwen2.5-Math-1.5B-Instruct",
    "./models/Qwen2.5-0.5B-Instruct",
)

_model = None
_tokenizer = None
_device: str | None = None
_active_model_dir: str | None = None
_load_lock = threading.Lock()
_generating = False

SYSTEM_PROMPT = (
    "Ты генератор LaTeX для домашних заданий. "
    "Вывод — ТОЛЬКО LaTeX code: с \\documentclass до \\end{document}. "
    "Без markdown (```), без текста до/после документа, без \\boxed и без решений."
)


def _dir_has_model(root: Path) -> bool:
    if not root.is_dir():
        return False
    has_config = (root / "config.json").is_file()
    has_weights = any(root.glob("*.safetensors")) or (root / "pytorch_model.bin").is_file()
    return has_config and has_weights


def resolve_model_dir() -> str | None:
    configured = Path(settings.local_model_dir)
    if _dir_has_model(configured):
        return str(configured)
    for rel in MODEL_DIR_CANDIDATES:
        p = Path(rel)
        if _dir_has_model(p):
            return str(p)
    return None


def local_model_available() -> bool:
    return resolve_model_dir() is not None


def is_model_loaded() -> bool:
    return _model is not None and _tokenizer is not None


def is_generating() -> bool:
    return _generating


def _resolve_device() -> str:
    import torch

    if torch.cuda.is_available():
        return "cuda"
    return "cpu"


def _load_model():
    global _model, _tokenizer, _device, _active_model_dir
    if _model is not None and _tokenizer is not None:
        return _model, _tokenizer, _device

    with _load_lock:
        if _model is not None and _tokenizer is not None:
            return _model, _tokenizer, _device

        path = resolve_model_dir()
        if not path:
            raise RuntimeError(
                "Модель не найдена. Запустите: python scripts/download_local_model.py"
            )

        try:
            import torch
            from transformers import AutoModelForCausalLM, AutoTokenizer
        except ImportError as e:
            raise RuntimeError(
                "Установите: pip install torch transformers accelerate safetensors"
            ) from e

        device = _resolve_device()
        logger.info("Загрузка модели %s (%s)...", path, device)
        t0 = time.perf_counter()

        _tokenizer = AutoTokenizer.from_pretrained(path, local_files_only=True)

        if device == "cuda":
            _model = AutoModelForCausalLM.from_pretrained(
                path,
                local_files_only=True,
                torch_dtype="auto",
                device_map="auto",
            )
        else:
            _model = AutoModelForCausalLM.from_pretrained(
                path,
                local_files_only=True,
                torch_dtype=torch.float32,
                low_cpu_mem_usage=True,
            )
            _model = _model.to("cpu")
            _model.eval()

        _device = device
        _active_model_dir = path
        logger.info("Модель загружена за %.1f с", time.perf_counter() - t0)
        return _model, _tokenizer, _device


def reset_model_cache() -> None:
    """Сброс после скачивания новой модели."""
    global _model, _tokenizer, _device, _active_model_dir
    _model = None
    _tokenizer = None
    _device = None
    _active_model_dir = None


def preload_model_background() -> None:
    def _run():
        if not local_model_available():
            return
        try:
            _load_model()
            logger.info("Предзагрузка модели завершена")
        except Exception as e:
            logger.warning("Предзагрузка модели не удалась: %s", e)

    threading.Thread(target=_run, daemon=True, name="local-llm-preload").start()


def generate_with_local_llm(
    student_name: str,
    subject: str,
    checklist: list[dict],
    grade: str = "",
) -> str:
    global _generating
    import torch

    _generating = True
    try:
        model, tokenizer, device = _load_model()

        user_prompt = build_homework_prompt(
            student_name, subject, checklist, grade
        )
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ]
        text = tokenizer.apply_chat_template(
            messages,
            tokenize=False,
            add_generation_prompt=True,
        )
        model_inputs = tokenizer([text], return_tensors="pt")
        if device == "cuda":
            target = model.device if hasattr(model, "device") else next(model.parameters()).device
            model_inputs = model_inputs.to(target)
        else:
            model_inputs = model_inputs.to("cpu")

        max_tokens = settings.local_model_max_tokens
        logger.info("Генерация (до %s токенов, %s)...", max_tokens, device)
        t0 = time.perf_counter()

        gen_kwargs: dict = {
            "max_new_tokens": max_tokens,
            "pad_token_id": tokenizer.eos_token_id,
        }
        if device == "cpu":
            gen_kwargs["do_sample"] = False
        else:
            gen_kwargs["do_sample"] = True
            gen_kwargs["temperature"] = 0.7

        with torch.inference_mode():
            generated_ids = model.generate(**model_inputs, **gen_kwargs)

        trimmed = [
            output_ids[len(input_ids) :]
            for input_ids, output_ids in zip(model_inputs.input_ids, generated_ids)
        ]
        response = tokenizer.batch_decode(trimmed, skip_special_tokens=True)[0]
        logger.info("Генерация завершена за %.1f с", time.perf_counter() - t0)

        if not response.strip():
            raise RuntimeError("Пустой ответ локальной модели")
        return sanitize_homework_response(response)
    finally:
        _generating = False


def get_local_model_info() -> dict:
    active = resolve_model_dir()
    device = "cpu"
    try:
        import torch

        device = "cuda" if torch.cuda.is_available() else "cpu"
    except ImportError:
        pass
    return {
        "model_id": settings.local_model_id,
        "dir": os.path.abspath(active) if active else settings.local_model_dir,
        "downloaded": local_model_available(),
        "loaded": is_model_loaded(),
        "generating": is_generating(),
        "device": device,
        "max_tokens": settings.local_model_max_tokens,
        "using_math_fallback": active and "Math" in active if active else False,
    }
