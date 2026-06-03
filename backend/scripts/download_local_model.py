#!/usr/bin/env python3
"""Скачивает Qwen с Hugging Face для transformers (без Ollama)."""

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from huggingface_hub import snapshot_download

MODELS = {
    "smart": ("Qwen/Qwen2.5-1.5B-Instruct", "Qwen2.5-1.5B-Instruct", "~3 ГБ, рекомендуется"),
    "instruct": ("Qwen/Qwen2.5-1.5B-Instruct", "Qwen2.5-1.5B-Instruct", "~3 ГБ"),
    "3b": ("Qwen/Qwen2.5-3B-Instruct", "Qwen2.5-3B-Instruct", "~6 ГБ, самая умная, долго на CPU"),
    "math": ("Qwen/Qwen2.5-Math-1.5B-Instruct", "Qwen2.5-Math-1.5B-Instruct", "~3 ГБ, только математика"),
    "fast": ("Qwen/Qwen2.5-0.5B-Instruct", "Qwen2.5-0.5B-Instruct", "~1 ГБ, быстрее на CPU"),
}

BACKEND_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def main():
    parser = argparse.ArgumentParser(description="Скачать Qwen с Hugging Face")
    parser.add_argument(
        "model",
        nargs="?",
        default="smart",
        choices=list(MODELS.keys()),
        help="smart | instruct | 3b | math | fast",
    )
    args = parser.parse_args()
    repo_id, folder, size_hint = MODELS[args.model]
    target = os.path.join(BACKEND_ROOT, "models", folder)

    os.makedirs(target, exist_ok=True)
    print(f"Скачивание {repo_id}")
    print(f"Папка: {target}")
    print(f"Размер {size_hint}")
    print()

    snapshot_download(repo_id=repo_id, local_dir=target)

    print()
    print("Готово. Перезапустите бэкенд.")
    if args.model in ("smart", "instruct"):
        print("Пропишите в backend/.env:")
        print("  LOCAL_MODEL_DIR=./models/Qwen2.5-1.5B-Instruct")
        print("  LOCAL_MODEL_ID=Qwen/Qwen2.5-1.5B-Instruct")
    if args.model == "fast":
        print("Быстрая 0.5B — только если нужна скорость, не качество.")


if __name__ == "__main__":
    main()
