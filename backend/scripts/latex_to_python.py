#!/usr/bin/env python3
"""
CLI: LaTeX из домашки -> Python-скрипт.

Примеры:
  python scripts/latex_to_python.py --text "$\\frac{2}{5}+\\frac{3}{5}$"
  python scripts/latex_to_python.py --html-file homework.html -o tasks.py
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.services.latex_convert import (
    build_python_script,
    extract_latex_expressions,
    homework_html_to_python_script,
    latex_to_python_expression,
    process_homework_html,
)


def main():
    parser = argparse.ArgumentParser(description="LaTeX -> Python script (RepetCRM)")
    parser.add_argument("--text", help="Строка с LaTeX ($...$)")
    parser.add_argument("--html-file", help="HTML-файл домашки")
    parser.add_argument("-o", "--output", help="Сохранить .py сюда")
    parser.add_argument("--preview-html", action="store_true", help="Показать HTML с картинками")
    args = parser.parse_args()

    if args.html_file:
        html = Path(args.html_file).read_text(encoding="utf-8")
    elif args.text:
        html = args.text
    else:
        html = (
            "<ul><li>Сумма: $\\frac{2}{5} + \\frac{3}{5}$</li>"
            "<li>Ещё: $\\frac{4}{7} + \\frac{1}{7}$</li></ul>"
        )
        print("Демо-режим (передайте --text или --html-file)\n")

    exprs = extract_latex_expressions(html)
    print(f"Найдено формул: {len(exprs)}")
    for i, e in enumerate(exprs, 1):
        print(f"  {i}. LaTeX: {e}")
        print(f"     Python: {latex_to_python_expression(e)}")

    script = homework_html_to_python_script(html)
    if args.output:
        Path(args.output).write_text(script, encoding="utf-8")
        print(f"\nСохранено: {args.output}")
    else:
        print("\n--- Python script ---\n")
        print(script)

    if args.preview_html:
        print("\n--- HTML preview ---\n")
        print(process_homework_html(html)[:2000])


if __name__ == "__main__":
    main()
