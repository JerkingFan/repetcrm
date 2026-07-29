"""
Конвертация LaTeX из домашних заданий:
1) в Python-скрипт (Fraction, sympy-подобные выражения)
2) в HTML с картинками формул (matplotlib) для PDF и просмотра
"""

from __future__ import annotations

import base64
import io
import re
from html import escape
from typing import Iterable

# $...$ и $$...$$
LATEX_INLINE_RE = re.compile(r"(?<!\$)\$(?!\$)(.+?)(?<!\$)\$(?!\$)", re.DOTALL)
LATEX_DISPLAY_RE = re.compile(r"\$\$(.+?)\$\$", re.DOTALL)
LATEX_PAREN_RE = re.compile(r"\\\((.+?)\\\)", re.DOTALL)
LATEX_BRACKET_RE = re.compile(r"\\\[(.*?)\\\]", re.DOTALL)


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


def _latex_to_mathtext(latex: str) -> str:
    """Минимальная нормализация для matplotlib mathtext."""
    s = latex.strip().strip("$")
    # matplotlib понимает \frac{}{}
    return s


def latex_to_png_base64(latex: str, fontsize: int = 16, dpi: int = 120) -> str | None:
    """Рендер одной формулы в PNG (base64)."""
    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        return None

    expr = _latex_to_mathtext(latex)
    fig = plt.figure(figsize=(0.01, 0.01))
    fig.text(0, 0, f"${expr}$", fontsize=fontsize)
    buf = io.BytesIO()
    fig.savefig(
        buf,
        format="png",
        dpi=dpi,
        bbox_inches="tight",
        pad_inches=0.08,
        transparent=False,
        facecolor="white",
    )
    plt.close(fig)
    buf.seek(0)
    return base64.b64encode(buf.read()).decode("ascii")


def _replace_latex_with_images(html: str) -> str:
    """Заменяет $...$ на <img> с PNG."""

    def repl_inline(m: re.Match) -> str:
        latex = m.group(1).strip()
        b64 = latex_to_png_base64(latex, fontsize=14)
        if b64:
            return (
                f'<img src="data:image/png;base64,{b64}" '
                f'alt="{escape(latex)}" class="latex-formula" '
                f'style="vertical-align:middle;max-height:1.6em;" />'
            )
        return f'<span class="latex-fallback">{escape(_latex_plain_fallback(latex))}</span>'

    def repl_display(m: re.Match) -> str:
        latex = m.group(1).strip()
        b64 = latex_to_png_base64(latex, fontsize=18)
        if b64:
            return (
                f'<div class="latex-display" style="margin:8px 0;text-align:center;">'
                f'<img src="data:image/png;base64,{b64}" alt="{escape(latex)}" />'
                f"</div>"
            )
        return f'<p class="latex-fallback">{escape(_latex_plain_fallback(latex))}</p>'

    def repl_bracket(m: re.Match) -> str:
        latex = m.group(1).strip()
        b64 = latex_to_png_base64(latex, fontsize=16)
        if b64:
            return (
                f'<img src="data:image/png;base64,{b64}" '
                f'alt="{escape(latex)}" class="latex-formula" '
                f'style="vertical-align:middle;max-height:1.8em;" />'
            )
        return f'<span class="latex-fallback">{escape(_latex_plain_fallback(latex))}</span>'

    out = LATEX_BRACKET_RE.sub(repl_bracket, html)
    out = LATEX_DISPLAY_RE.sub(repl_display, out)
    out = LATEX_PAREN_RE.sub(repl_inline, out)
    out = LATEX_INLINE_RE.sub(repl_inline, out)
    return out


def _fix_math_superscripts(expr: str) -> str:
    """\\sin^2x → \\sin^{2}x для mathtext."""
    s = expr
    s = re.sub(r"\\(sin|cos|tan|cot|log|ln)\^(\d+)([a-zA-Z])", r"\\\1^{\2}\3", s)
    s = re.sub(r"([a-zA-Z0-9])\^(\d+)(?![{\d])", r"\1^{\2}", s)
    s = re.sub(r"(\d+)\^\\circ\b", r"\1^{\\circ}", s)
    s = re.sub(r"(\d+)\^\{\\circ\}", r"\1^{\\circ}", s)
    return s


_SUPERSCRIPT_DIGITS = "⁰¹²³⁴⁵⁶⁷⁸⁹"


def _to_superscript(num_str: str) -> str:
    if num_str.isdigit() and len(num_str) <= 2:
        return "".join(_SUPERSCRIPT_DIGITS[int(c)] for c in num_str)
    return "^" + num_str


def _latex_to_unicode(expr: str) -> str:
    """LaTeX-фрагмент → читаемый текст для PDF без рендера."""
    s = _fix_mathtext_expr(_fix_math_superscripts(expr.strip().strip("$")))
    reps: list[tuple[str, str]] = [
        (r"\\pi\b", "π"),
        (r"\\alpha\b", "α"),
        (r"\\beta\b", "β"),
        (r"\\theta\b", "θ"),
        (r"\\leq\b", "≤"),
        (r"\\geq\b", "≥"),
        (r"\\le\b", "≤"),
        (r"\\ge\b", "≥"),
        (r"\\neq\b", "≠"),
        (r"\\cdot\b", "·"),
        (r"\\times\b", "×"),
        (r"\\ldots\b", "…"),
        (r"\\circ\b", "°"),
        (r"\\sin\b", "sin"),
        (r"\\cos\b", "cos"),
        (r"\\tan\b", "tan"),
        (r"\\cot\b", "cot"),
        (r"\\frac\s*\{([^{}]+)\}\s*\{([^{}]+)\}", r"\1/\2"),
        (r"\\sqrt\s*\{([^{}]+)\}", r"√(\1)"),
        (r"\\left\s*", ""),
        (r"\\right\s*", ""),
    ]
    for pat, repl in reps:
        s = re.sub(pat, repl, s)
    s = re.sub(r"_\{([^{}]+)\}", r"_\1", s)
    s = re.sub(
        r"\^\{([^{}]+)\}",
        lambda m: _to_superscript(m.group(1))
        if m.group(1).isdigit()
        else "^" + m.group(1),
        s,
    )
    s = re.sub(
        r"([a-zA-Z0-9])\^(\d+)\b",
        lambda m: m.group(1) + _to_superscript(m.group(2)),
        s,
    )
    s = re.sub(r"\\[a-zA-Z]+\b", "", s)
    s = s.replace("{", "").replace("}", "")
    s = re.sub(r"\s+", " ", s).strip()
    return s


def _latex_plain_fallback(latex: str) -> str:
    return _latex_to_unicode(latex)


def _wrap_bare_latex_segment(segment: str) -> str:
    """Оборачивает голый LaTeX только в фрагменте без $...$."""
    if not segment.strip():
        return segment

    t = segment
    t = re.sub(
        r"\[\s*0\s*,\s*2\\pi\s*\]",
        lambda _: "$[0, 2\\pi]$",
        t,
        flags=re.I,
    )
    t = re.sub(
        r"\(\s*0\s*;\s*2\\pi\s*\)",
        lambda _: "$(0; 2\\pi)$",
        t,
        flags=re.I,
    )

    bare = re.compile(
        r"(?:\\(?:frac|sqrt|sin|cos|tan|cot|log|ln|pi|alpha|beta|theta|le|ge|leq|geq|cdot|times|div)"
        r"(?:\s*\{[^{}]*\}){0,2}"
        r"(?:\s*[_^](?:\{[^{}]*\}|[a-zA-Z0-9]+))?"
        r"(?:\s*[0-9a-zA-Z+\-*/=<>.,;(){}\[\]|\\]+)*"
        r")+"
        r"|\d+\\pi\b"
        r"|\[[^\]]*2\\pi[^\]]*\]",
        re.I,
    )

    out: list[str] = []
    pos = 0
    for m in bare.finditer(t):
        out.append(t[pos : m.start()])
        chunk = m.group(0).strip()
        if chunk:
            chunk = _fix_math_superscripts(chunk)
            # Пунктуация после формулы — вне $
            trail = ""
            while chunk and chunk[-1] in ".,;:!?":
                trail = chunk[-1] + trail
                chunk = chunk[:-1].rstrip()
            out.append(f"${chunk}$" if chunk else "")
            out.append(trail)
        pos = m.end()
    out.append(t[pos:])
    return "".join(out)


def _join_text_and_math(parts: list[str]) -> str:
    """Склеивает куски текста и $...$ с пробелами там, где нужно."""
    result: list[str] = []
    for part in parts:
        if not part:
            continue
        p = part.lstrip()
        if not p:
            continue
        if result:
            prev = result[-1].rstrip()
            p0 = p.lstrip()
            if (
                (prev.endswith("$") and p0.startswith("$"))
                or (prev[-1:].isalnum() and p0.startswith("$"))
                or (prev.endswith("$") and p0[:1].isalnum())
            ):
                result.append(" ")
        result.append(part)
    return "".join(result)


def ensure_inline_math_delimiters(text: str) -> str:
    """Оборачивает «голый» LaTeX в $...$; не трогает уже обёрнутые формулы."""
    t = normalize_math_delimiters(text.strip())
    if not t:
        return t

    parts: list[str] = []
    last = 0
    for m in LATEX_INLINE_RE.finditer(t):
        before = t[last : m.start()]
        if before:
            parts.append(_wrap_bare_latex_segment(before))
        inner = _normalize_math_segment(m.group(1))
        parts.append(f"${inner}$")
        last = m.end()
    tail = t[last:]
    if tail:
        parts.append(_wrap_bare_latex_segment(tail))
    if not parts:
        return _wrap_bare_latex_segment(t)
    return _join_text_and_math(parts)


def _insert_trig_spaces(s: str) -> str:
    """sinacosβ → sin α cos β (для текста без LaTeX)."""
    t = s
    for ch, name in (("α", "α"), ("β", "β"), ("π", "π"), ("θ", "θ")):
        t = t.replace(ch, f" {name} ")
    for fn in ("arcsin", "arccos", "arctan", "sin", "cos", "tan", "cot"):
        t = re.sub(rf"(?<!\\)(?<![a-z]){fn}(?![a-z])", f" {fn} ", t, flags=re.I)
    t = re.sub(r"\^\((\d+)\)", lambda m: "²³⁴⁵⁶⁷⁸⁹"[int(m.group(1)) - 1] if m.group(1).isdigit() and 1 <= int(m.group(1)) <= 9 else f"^{m.group(1)}", t)
    t = re.sub(r"\^2\b", "²", t)
    t = re.sub(r"\^3\b", "³", t)
    t = re.sub(r"\s*([≤≥<>])\s*", r" \1 ", t)
    t = re.sub(r"\s+", " ", t).strip()
    return t


def _normalize_math_segment(expr: str) -> str:
    """Нормализация содержимого $...$ для pdflatex/matplotlib."""
    s = expr.strip().strip("$")
    if not s:
        return s
    s = _fix_mathtext_expr(_fix_math_superscripts(s))
    return s.strip()


def format_task_for_display(task: str) -> str:
    """Задача с единообразными $...$ для превью и рендера формул."""
    t = clean_latex_task_text(task)
    t = normalize_math_delimiters(t)
    return ensure_inline_math_delimiters(t)


def fix_task_math_latex(task: str) -> str:
    """Готовит условие задачи к компиляции pdflatex: не ломает $n$, $a_1$ и т.п."""
    t = task.strip()
    if not t:
        return t
    for ch, cmd in (
        ("α", r"\alpha"),
        ("β", r"\beta"),
        ("π", r"\pi"),
        ("θ", r"\theta"),
        ("≤", r"\le"),
        ("≥", r"\ge"),
    ):
        t = t.replace(ch, " " + cmd + " ")
    for fn in ("arcsin", "arccos", "arctan", "sin", "cos", "tan", "cot"):
        t = re.sub(rf"(?<!\\)(?<![a-z]){fn}(?![a-z])", rf"\\{fn} ", t, flags=re.I)
    t = re.sub(r"(?<!\\)\ble\b", r"\\le ", t)
    t = re.sub(r"(?<!\\)\bge\b", r"\\ge ", t)
    t = re.sub(r"\s+", " ", t).strip()

    parts: list[str] = []
    last = 0
    for m in LATEX_INLINE_RE.finditer(t):
        before = t[last : m.start()]
        if before.strip():
            parts.append(_wrap_bare_latex_segment(before))
        inner = _normalize_math_segment(m.group(1))
        parts.append(f"${inner}$")
        last = m.end()
    tail = t[last:]
    if tail.strip():
        parts.append(_wrap_bare_latex_segment(tail))
    result = _join_text_and_math(parts) if parts else _wrap_bare_latex_segment(t)
    if "$" not in result and re.search(r"\\[a-zA-Z]|[_^]", result):
        result = ensure_inline_math_delimiters(result)
    return result


def build_print_tex_document(
    content: str,
    lesson_date,
    *,
    subject: str = "предмету",
    student_name: str = "",
) -> str:
    """Собирает чистый .tex для PDF (enumerate + нормальные формулы)."""
    from app.services.latex_compile import PDFLATEX_PREAMBLE

    sections = parse_latex_homework(content)
    if not sections:
        sections = parse_homework_content(content)
    if not sections:
        raise ValueError("Нет задач для PDF")

    date_s = lesson_date.strftime("%d.%m.%Y") if hasattr(lesson_date, "strftime") else str(lesson_date)
    subj = subject.replace("_", r"\_")
    lines = [
        PDFLATEX_PREAMBLE,
        r"\begin{document}",
        f"\\title{{Домашнее задание по {subj}}}",
        f"\\author{{Ученик: {student_name}}}" if student_name else "",
        f"\\date{{{date_s}}}",
        r"\maketitle",
    ]
    for title, tasks in sections:
        if title:
            lines.append(f"\\section*{{{title}}}")
        lines.append(r"\begin{enumerate}")
        for task in tasks:
            lines.append(f"\\item {fix_task_math_latex(task)}")
        lines.append(r"\end{enumerate}")
    lines.append(r"\end{document}")
    return "\n".join(ln for ln in lines if ln)


def latex_line_to_readable_plain(text: str) -> str:
    """Вся строка задачи — читаемый текст (без сырого \\sin и $)."""
    t = normalize_math_delimiters(text.strip())
    if not t:
        return t
    t = ensure_inline_math_delimiters(t)

    def repl(m: re.Match) -> str:
        return _latex_to_unicode(m.group(1))

    for pat in (LATEX_DISPLAY_RE, LATEX_BRACKET_RE, LATEX_PAREN_RE, LATEX_INLINE_RE):
        t = pat.sub(repl, t)
    if "\\" in t:
        t = _latex_to_unicode(t)
    t = re.sub(r"\$+", "", t)
    return _insert_trig_spaces(t)


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


def _lines_from_body(block: str) -> list[str]:
    tasks = re.findall(
        r"\\begin\s*\{\s*task\s*\}(.*?)\\end\s*\{\s*task\s*\}",
        block,
        re.DOTALL | re.IGNORECASE,
    )
    if tasks:
        return [clean_latex_task_text(t) for t in tasks if t.strip()]
    paras = [p.strip() for p in re.split(r"\n\s*\n+", block) if p.strip() and not p.strip().startswith("%")]
    if not paras:
        paras = [ln.strip() for ln in block.splitlines() if ln.strip() and not ln.strip().startswith("%")]
    return [normalize_math_delimiters(p) for p in paras if p]


def parse_homework_content(text: str) -> list[tuple[str, list[str]]]:
    """LaTeX / HTML / текст → секции и строки для PDF."""
    if not text or not text.strip():
        return []

    structured = parse_latex_homework(text)
    if structured:
        return [
            (title, [clean_latex_task_text(t) for t in tasks])
            for title, tasks in structured
        ]

    raw = text.strip()
    doc = re.search(
        r"\\begin\s*\{\s*document\s*\}(.*?)\\end\s*\{\s*document\s*\}",
        raw,
        re.DOTALL | re.IGNORECASE,
    )
    body = doc.group(1) if doc else raw
    for pat in (r"\\title\{[^}]*\}", r"\\author\{[^}]*\}", r"\\date\{[^}]*\}", r"\\maketitle"):
        body = re.sub(pat, "", body, flags=re.DOTALL | re.IGNORECASE)

    sections = re.findall(
        r"\\section\s*\{([^}]*)\}(.*?)(?=\\section\s*\{|$)",
        body,
        re.DOTALL | re.IGNORECASE,
    )
    if sections:
        out: list[tuple[str, list[str]]] = []
        for title, block in sections:
            lines = _lines_from_body(block)
            if lines:
                out.append((title.strip(), lines))
        if out:
            return out

    lines = _lines_from_body(body)
    if lines:
        return [("", lines)]

    if raw.lstrip().startswith("<"):
        from app.services.pdf import _parse_html_blocks  # circular?

        blocks = _parse_html_blocks_for_pdf(raw)
        if blocks:
            return blocks

    plain_lines = [normalize_math_delimiters(ln) for ln in raw.splitlines() if ln.strip()]
    return [("", plain_lines)] if plain_lines else []


def _parse_html_blocks_for_pdf(html: str) -> list[tuple[str, list[str]]]:
    import re as _re

    sections: list[tuple[str, list[str]]] = []
    current_title = ""
    current_lines: list[str] = []
    for m in _re.finditer(
        r"<h3[^>]*>(.*?)</h3>|<li[^>]*>(.*?)</li>|<p[^>]*>(.*?)</p>",
        html,
        _re.I | _re.DOTALL,
    ):
        if m.group(1):
            if current_lines:
                sections.append((current_title, current_lines))
            current_title = _re.sub(r"<[^>]+>", "", m.group(1)).strip()
            current_lines = []
        elif m.group(2):
            line = _re.sub(r"<[^>]+>", "", m.group(2)).strip()
            if line:
                current_lines.append(normalize_math_delimiters(line))
        elif m.group(3):
            line = _re.sub(r"<[^>]+>", "", m.group(3)).strip()
            if line:
                current_lines.append(normalize_math_delimiters(line))
    if current_lines:
        sections.append((current_title, current_lines))
    return sections


def line_has_math(text: str) -> bool:
    return bool(
        re.search(r"\$[^$]+\$", text)
        or re.search(
            r"\\(?:frac|sqrt|sin|cos|tan|cot|pi|alpha|beta|theta|le|ge|leq|geq|cdot|times)\b",
            text,
            re.I,
        )
        or re.search(r"\d+\s*\\pi\b", text, re.I)
    )


def _fix_mathtext_expr(expr: str) -> str:
    """LaTeX-обозначения, которые matplotlib mathtext не понимает."""
    s = expr.strip()
    for old, new in (
        (r"\tg", r"\tan"),
        (r"\ctg", r"\cot"),
        (r"\arctg", r"\arctan"),
        (r"\arcctg", r"\arccot"),
    ):
        s = s.replace(old, new)
    return s


def _normalize_line_for_matplotlib(line: str) -> str:
    def repl(m: re.Match) -> str:
        return f"${_fix_mathtext_expr(m.group(1))}$"

    out = line
    for pat in (LATEX_INLINE_RE, LATEX_PAREN_RE, LATEX_BRACKET_RE):
        out = pat.sub(repl, out)
    return out


def line_to_plain_pdf_text(text: str) -> str:
    """Текст задачи без PNG — для fallback в PDF."""
    return latex_line_to_readable_plain(text)


def render_mixed_line_png(text: str, dpi: int = 140) -> bytes | None:
    """Строка с русским текстом и $...$ → PNG для вставки в PDF."""
    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        return None

    line = _normalize_line_for_matplotlib(ensure_inline_math_delimiters(text.strip()))
    if not line:
        return None

    try:
        plt.rcParams["font.sans-serif"] = ["DejaVu Sans", "Arial", "sans-serif"]
        plt.rcParams["axes.unicode_minus"] = False

        n_math = len(re.findall(r"\$[^$]+\$", line))
        height = min(3.2, 0.55 + 0.14 * max(1, n_math))
        fig, ax = plt.subplots(figsize=(7.2, height))
        ax.axis("off")
        fig.text(
            0.02,
            0.95,
            line,
            fontsize=11,
            va="top",
            ha="left",
            wrap=True,
        )
        buf = io.BytesIO()
        fig.savefig(
            buf,
            format="png",
            dpi=dpi,
            bbox_inches="tight",
            pad_inches=0.12,
            facecolor="white",
        )
        plt.close(fig)
        buf.seek(0)
        return buf.read()
    except Exception:
        return None


def latex_document_to_html(latex: str) -> str | None:
    """LaTeX article с \\section и task → HTML для CRM/PDF."""
    if not latex or not re.search(r"\\begin\s*\{\s*document\s*\}|\\section\s*\{", latex, re.I):
        return None

    text = latex.strip()
    doc = re.search(
        r"\\begin\s*\{\s*document\s*\}(.*?)\\end\s*\{\s*document\s*\}",
        text,
        re.DOTALL | re.IGNORECASE,
    )
    body = doc.group(1) if doc else text

    for pat in (
        r"\\documentclass.*?(?=\\begin\s*\{\s*document\s*\}|\\section|\\begin\s*\{\s*task\s*\})",
        r"\\usepackage\{[^}]*\}",
        r"\\usepackage\[[^\]]*\]\{[^}]*\}",
        r"\\geometry\{[^}]*\}",
        r"\\newenvironment\{task\}.*?(?=\\begin\s*\{\s*document\s*\}|\\section|\\begin\s*\{\s*task\s*\})",
        r"\\title\{[^}]*\}",
        r"\\author\{[^}]*\}",
        r"\\date\{[^}]*\}",
        r"\\maketitle",
        r"%.*",
    ):
        body = re.sub(pat, "", body, flags=re.DOTALL | re.IGNORECASE)

    sections = re.findall(
        r"\\section\s*\{([^}]*)\}(.*?)(?=\\section\s*\{|$)",
        body,
        re.DOTALL | re.IGNORECASE,
    )
    parts: list[str] = ["<h2>Домашнее задание</h2>"]

    def _tasks_from_block(block: str) -> list[str]:
        tasks = re.findall(
            r"\\begin\s*\{\s*task\s*\}(.*?)\\end\s*\{\s*task\s*\}",
            block,
            re.DOTALL | re.IGNORECASE,
        )
        if tasks:
            return [clean_latex_task_text(t) for t in tasks if t.strip()]
        lines = [ln.strip() for ln in block.splitlines() if ln.strip() and not ln.strip().startswith("%")]
        return [clean_latex_task_text(ln) for ln in lines if ln]

    if sections:
        for title, block in sections:
            title = title.strip()
            if title:
                parts.append(f"<h3>{escape(clean_latex_task_text(title))}</h3>")
            items = _tasks_from_block(block)
            if items:
                parts.append("<ul>")
                for item in items:
                    parts.append(f"<li>{escape(format_task_for_display(item))}</li>")
                parts.append("</ul>")
    else:
        items = _tasks_from_block(body)
        if items:
            parts.append("<ul>")
            for item in items:
                parts.append(f"<li>{escape(format_task_for_display(item))}</li>")
            parts.append("</ul>")

    html = "\n".join(parts)
    return html if re.search(r"<li>", html, re.I) else None


def prepare_html_for_pdf(html: str) -> str:
    """Для PDF: без картинок формул, только текст (иначе ломается вёрстка)."""
    if not html:
        return html
    html = re.sub(r"<img[^>]*>", "", html, flags=re.I)

    def repl(m: re.Match) -> str:
        return escape(_latex_plain_fallback(m.group(1)))

    for pat in (LATEX_PAREN_RE, LATEX_DISPLAY_RE, LATEX_INLINE_RE):
        html = pat.sub(repl, html)
    return html


def process_homework_html(html: str, render_images: bool = True) -> str:
    """
    Обрабатывает HTML домашки: LaTeX -> картинки (или unicode fallback).
    """
    if not html or "$" not in html:
        return html
    if render_images:
        try:
            return _replace_latex_with_images(html)
        except Exception:
            pass
    # fallback: unicode дроби в тексте
    def repl(m: re.Match) -> str:
        return escape(_latex_plain_fallback(m.group(1)))

    out = LATEX_DISPLAY_RE.sub(lambda m: f"<p><strong>{repl(m)}</strong></p>", html)
    out = LATEX_INLINE_RE.sub(repl, out)
    return out


def homework_html_to_python_script(html: str) -> str:
    """Полный Python-скрипт по всем формулам из HTML домашки."""
    return build_python_script(extract_latex_expressions(html))
