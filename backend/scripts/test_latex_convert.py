#!/usr/bin/env python3
"""Quick checks for latex_convert."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.services.latex_convert import (
    ensure_inline_math_delimiters,
    extract_latex_expressions,
    fix_task_math_latex,
    format_task_for_display,
    latex_line_to_readable_plain,
    latex_to_python_expression,
    latex_document_to_html,
    process_homework_html,
)

SAMPLES = [
    r"Найдите: $\frac{1}{5}+\frac{2}{5}$",
    r"Решите на $[0; 2\pi]$: $\sin x \geq \frac{1}{2}$.",
    r"Упростите: $\sin^2 x + \cos^2 x$ при $x = \frac{\pi}{4}$.",
    r"Запишите формулу для $n$ чисел $a_1,\ldots,a_n$.",
    r"Температура: $12^\circ$, $15^\circ$, $18^\circ$.",
    r"Сумма обыкновенных дробей: $\frac{2}{5} + \frac{3}{5}$",
]

def main():
    for s in SAMPLES:
        print("IN:", s)
        print("  exprs:", extract_latex_expressions(s))
        print("  py:", [latex_to_python_expression(e) for e in extract_latex_expressions(s)])
        print("  plain:", latex_line_to_readable_plain(s))
        print("  fix:", fix_task_math_latex(s))
        print("  display:", format_task_for_display(s))
        print()

    bad = [
        r"для $n$ чисел $a_1,\ldots,a_n$.",
        r"Пусть a и b — углы. Докажите: \sin a \cos b \ge \frac{1}{2} \sin(a+b).",
        r"Найдите $x$ на $[0, 2\pi]$: $\sin^2x + 2\cos^2x \le 1$.",
    ]
    for s in bad:
        print("FIX:", s)
        print(" ->", fix_task_math_latex(s))
        print()

    doc = r"""
\documentclass{article}
\begin{document}
\section{Дроби}
\begin{task} Вычислите: $\frac{2}{5}+\frac{3}{5}$ \end{task}
\begin{task} Решите на $[0; 2\pi]$: $\sin x \geq \frac{1}{2}$. \end{task}
\end{document}
"""
    html = latex_document_to_html(doc)
    print("HTML:", html[:500] if html else None)
    if html:
        rendered = process_homework_html(html, render_images=False)
        print("RENDERED:", rendered[:500])

if __name__ == "__main__":
    main()
