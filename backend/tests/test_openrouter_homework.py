"""Прямой OpenRouter для домашки."""

import pytest

from app.services.openrouter_homework import (
    build_direct_homework_messages,
    finalize_openrouter_homework,
)


def test_build_direct_homework_messages_short_and_clear():
    msgs = build_direct_homework_messages(
        "Аня",
        "Математика",
        [{"topic": "Логарифмы", "understanding": 3, "difficulty": "medium"}],
        "10",
    )
    assert len(msgs) == 2
    assert "Логарифмы" in msgs[1]["content"]
    assert "\\documentclass" in msgs[0]["content"]
    assert "x^2-5x+6" not in msgs[1]["content"]


def test_finalize_accepts_latex_document():
    raw = r"""
```latex
\documentclass{article}
\begin{document}
\section{Дроби}
\begin{task}Вычислите $\frac{1}{2}+\frac{1}{3}$.\end{task}
\end{document}
```
"""
    out = finalize_openrouter_homework(raw)
    assert r"\documentclass" in out
    assert r"\begin{task}" in out
    assert r"\end{document}" in out


def test_finalize_appends_end_document():
    raw = r"\documentclass{article}\begin{document}\begin{task}$x+1=2$\end{task}"
    out = finalize_openrouter_homework(raw)
    assert out.endswith(r"\end{document}")
