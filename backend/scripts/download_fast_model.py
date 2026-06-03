#!/usr/bin/env python3
"""Скачивает лёгкую GGUF ~500 МБ — генерация за 20–60 сек на CPU."""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from huggingface_hub import hf_hub_download

from app.config import settings

REPO = "Qwen/Qwen2.5-0.5B-Instruct-GGUF"
FILENAME = "qwen2.5-0.5b-instruct-q4_k_m.gguf"
BACKEND_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TARGET = os.path.join(BACKEND_ROOT, "models", FILENAME)


def main():
    os.makedirs(os.path.dirname(TARGET), exist_ok=True)
    print(f"Скачивание {FILENAME} (~500 МБ)...")
    hf_hub_download(repo_id=REPO, filename=FILENAME, local_dir=os.path.dirname(TARGET))
    final = os.path.join(os.path.dirname(TARGET), FILENAME)
    print(f"Готово: {final}")
    print("Перезапустите бэкенд — генерация станет намного быстрее.")


if __name__ == "__main__":
    main()
