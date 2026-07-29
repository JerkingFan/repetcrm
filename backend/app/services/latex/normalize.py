"""LaTeX normalization, parsing, Python expression export."""
from __future__ import annotations

import re
from typing import Iterable

from app.services.latex.patterns import (
    LATEX_BRACKET_RE,
    LATEX_DISPLAY_RE,
    LATEX_INLINE_RE,
    LATEX_PAREN_RE,
)

def clean_latex_task_text(text: str) -> str:
    """Убирает \\textbf и служебные префиксы — для PDF/превью."""
    t = text.strip()
    for _ in range(3):
        t = re.sub(r"\\textbf\{([^{}]*)\}", r"\1", t)
        t = re.sub(r"\\textit\{([^{}]*)\}", r"\1", t)
        t = re.sub(r"\\emph\{([^{}]*)\}", r"\1", t)
        t = re.sub(r"\\text\{([^{}]*)\}", r"\1", t)
    t = re.sub(r"^(?:\\textbf\s*)?(?:Задача\s*\d*[\.\):]?\s*)+", "", t, flags=re.I)
    t = re.sub(r"^Памятка:\s*", "", t, flags=re.I)
    return normalize_math_delimiters(re.sub(r"\s+", " ", t).strip())


def _dedupe_tasks(tasks: list[str], max_count: int) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for t in tasks:
        key = re.sub(r"\d+", "N", t.lower().strip())
        if key in seen:
            continue
        seen.add(key)
        out.append(t)
        if len(out) >= max_count:
            break
    return out


def _canonical_section_title(title: str) -> str:
    t = title.strip()
    t = re.sub(r"^Памятка:\s*", "", t, flags=re.I)
    return t.strip() or title.strip()


def is_latex_homework_raw(text: str) -> bool:
    return bool(
        text
        and (
            re.search(r"\\documentclass", text, re.I)
            or re.search(r"\\begin\s*\{\s*document\s*\}", text, re.I)
            or (
                re.search(r"\\section\s*\{", text, re.I)
                and re.search(r"\\begin\s*\{\s*task\s*\}", text, re.I)
            )
        )
    )


def parse_latex_homework(latex: str) -> list[tuple[str, list[str]]]:
    """Разбор LaTeX-документа: [(название секции, [задачи]), ...]."""
    if not latex or not is_latex_homework_raw(latex):
        return []

    text = latex.strip()
    doc = re.search(
        r"\\begin\s*\{\s*document\s*\}(.*?)\\end\s*\{\s*document\s*\}",
        text,
        re.DOTALL | re.IGNORECASE,
    )
    body = doc.group(1) if doc else text

    for pat in (
        r"\\title\{[^}]*\}",
        r"\\author\{[^}]*\}",
        r"\\date\{[^}]*\}",
        r"\\maketitle",
    ):
        body = re.sub(pat, "", body, flags=re.DOTALL | re.IGNORECASE)

    def _tasks_from_block(block: str) -> list[str]:
        tasks = re.findall(
            r"\\begin\s*\{\s*task\s*\}(.*?)\\end\s*\{\s*task\s*\}",
            block,
            re.DOTALL | re.IGNORECASE,
        )
        if tasks:
            return [clean_latex_task_text(t) for t in tasks if t.strip()]
        return []

    sections = re.findall(
        r"\\section\s*\{([^}]*)\}(.*?)(?=\\section\s*\{|$)",
        body,
        re.DOTALL | re.IGNORECASE,
    )
    result: list[tuple[str, list[str]]] = []
    if sections:
        for title, block in sections:
            items = _tasks_from_block(block)
            if items:
                result.append((title.strip(), items))
    else:
        items = _tasks_from_block(body)
        if items:
            result.append(("", items))
    return result


def normalize_homework_latex_document(latex: str, max_per_topic: int = 9) -> str:
    """Чистит задачи, сливает дубли секций, ограничивает число заданий на тему."""
    text = latex.strip()
    if not is_latex_homework_raw(text):
        return text

    doc = re.search(
        r"(\\documentclass[\s\S]*?\\begin\s*\{\s*document\s*\})",
        text,
        re.DOTALL | re.IGNORECASE,
    )
    footer = re.search(r"\\end\s*\{\s*document\s*\}", text, re.I)
    prefix = doc.group(1) if doc else "\\begin{document}"
    suffix = footer.group(0) if footer else "\\end{document}"
    prefix = re.sub(
        r"\\newenvironment\{task\}\{[^}]*\\textbf\{Задача\.?\}[^}]*\}",
        r"\\newenvironment{task}{\\par\\noindent}{\\par\\medskip}",
        prefix,
        flags=re.I,
    )

    sections = parse_latex_homework(text)
    if not sections:
        return text

    merged: dict[str, list[str]] = {}
    for title, tasks in sections:
        key = _canonical_section_title(title)
        cleaned = [clean_latex_task_text(t) for t in tasks if clean_latex_task_text(t)]
        if key in merged:
            cleaned = _dedupe_tasks(merged[key] + cleaned, max_per_topic)
        else:
            cleaned = _dedupe_tasks(cleaned, max_per_topic)
        if cleaned:
            merged[key] = cleaned

    body_parts: list[str] = []
    for title, cleaned in merged.items():
        body_parts.append(f"\\section{{{title}}}")
        for task in cleaned:
            body_parts.append(f"\\begin{{task}} {task} \\end{{task}}")

    if not body_parts:
        return text
    return prefix + "\n" + "\n".join(body_parts) + "\n" + suffix


def normalize_math_delimiters(text: str) -> str:
    """\\[ \\], \\( \\), $$ $$ → $...$ для matplotlib и FPDF."""
    if not text:
        return text
    t = text
    t = LATEX_BRACKET_RE.sub(lambda m: f" ${m.group(1).strip()}$ ", t)
    t = LATEX_PAREN_RE.sub(lambda m: f" ${m.group(1).strip()}$ ", t)
    t = LATEX_DISPLAY_RE.sub(lambda m: f" ${m.group(1).strip()}$ ", t)
    return re.sub(r"  +", " ", t).strip()


def content_has_raw_latex_delimiters(text: str) -> bool:
    return bool(re.search(r"\\\[[\s\S]*?\\\]|\\\([\s\S]*?\\\)", text))


def _is_meaningful_latex_expr(expr: str) -> bool:
    """Отсекает одиночные $n$, $x$ — не полноценные формулы."""
    e = expr.strip()
    if not e:
        return False
    if len(e) == 1 and e.isalpha():
        return False
    if re.search(r"\\|frac|sqrt|[_^={}\[\]()]|geq|leq|cdot|times|pi\b", e, re.I):
        return True
    return len(e) > 3


def extract_latex_expressions(text: str) -> list[str]:
    """Все формулы из текста/HTML."""
    found: list[str] = []
    for pat in (LATEX_BRACKET_RE, LATEX_DISPLAY_RE, LATEX_PAREN_RE, LATEX_INLINE_RE):
        for m in pat.finditer(text):
            expr = m.group(1).strip()
            if expr and expr not in found and _is_meaningful_latex_expr(expr):
                found.append(expr)
    return found


def latex_to_python_expression(latex: str) -> str:
    """
    LaTeX -> Python-выражение.
    \\frac{2}{5} -> Fraction(2, 5); \\frac{\\pi}{4} остаётся делением.
    """

    def frac_repl(m: re.Match) -> str:
        a, b = m.group(1).strip(), m.group(2).strip()
        if re.fullmatch(r"-?\d+", a) and re.fullmatch(r"-?\d+", b):
            return f"Fraction({a}, {b})"
        return f"({latex_to_python_expression(a)})/({latex_to_python_expression(b)})"

    s = latex.strip().strip("$").strip()
    s = re.sub(r"\\frac\s*\{([^{}]+)\}\s*\{([^{}]+)\}", frac_repl, s)
    s = re.sub(r"\\dfrac\s*\{([^{}]+)\}\s*\{([^{}]+)\}", frac_repl, s)
    s = s.replace(r"\cdot", " * ").replace(r"\times", " * ").replace(r"\div", " / ")
    s = re.sub(r"\\sqrt\s*\{([^{}]+)\}", r"sqrt(\1)", s)
    s = re.sub(r"\\left\s*|\s*\\right\s*", "", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def build_python_script(
    latex_list: Iterable[str],
    title: str = "Домашнее задание — выражения из LaTeX",
) -> str:
    """Собирает исполняемый .py скрипт из списка LaTeX-формул."""
    lines = [
        '#!/usr/bin/env python3',
        '"""',
        title,
        "Сгенерировано RepetCRM (latex_convert).",
        '"""',
        "from fractions import Fraction",
        "from math import sqrt",
        "",
        "def eval_expr(code: str):",
        '    """Безопасный eval только для Fraction и sqrt."""',
        "    allowed = {\"Fraction\": Fraction, \"sqrt\": sqrt}",
        "    return eval(code, {" + '"__builtins__": {}' + ", **allowed})",
        "",
        "TASKS = [",
    ]
    for i, latex in enumerate(latex_list, 1):
        py = latex_to_python_expression(latex)
        safe_latex = latex.replace('"', '\\"')
        lines.append(f'    ({i}, "{safe_latex}", "{py}"),')
    lines.extend(
        [
            "]",
            "",
            "if __name__ == \"__main__\":",
            "    print(\"=\" * 50)",
            "    for num, latex, code in TASKS:",
            "        try:",
            "            value = eval_expr(code)",
            "            print(f\"{num}. LaTeX: {latex}\")",
            "            print(f\"   Python: {code}\")",
            "            print(f\"   Значение: {value}\")",
            "            print()",
            "        except Exception as e:",
            "            print(f\"{num}. Ошибка для {code}: {e}\")",
            "",
        ]
    )
    return "\n".join(lines)


