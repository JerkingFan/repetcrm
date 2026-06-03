"""Проверка, хранение и преобразование домашнего задания (LaTeX / HTML)."""

import logging
import re
from collections import Counter

logger = logging.getLogger(__name__)

BAD_MARKERS = (
    r"\boxed",
    "scope this task",
    "ham通用",
    "ham generalities",
    "tokenize=False",
    "apply_chat_template",
    "requirements:",
    "The final answer is",
    "Пred带",
)

# Фразы из примера в промпте — модель часто копирует их во все секции
PROMPT_ECHO_MARKERS = (
    "x^2 - 5x + 6 = 0",
    "x^2-5x+6=0",
    "2x^2 + ax + 3 = 0",
    "единственный корень",
)

MIN_CYRILLIC_RATIO = 0.05

_PLACEHOLDER_PHRASES: set[str] | None = None


def _placeholder_phrases() -> set[str]:
    global _PLACEHOLDER_PHRASES
    if _PLACEHOLDER_PHRASES is None:
        from app.services.homework_prefs import TASK_TYPE_LABELS

        _PLACEHOLDER_PHRASES = {v.lower() for v in TASK_TYPE_LABELS.values()}
        _PLACEHOLDER_PHRASES.update(
            {
                "упражнения на отработку формул/правил",
                "текстовые задачи",
                "тестовые задания",
                "творческие задания",
                "задания с выбором ответа",
                "задания с открытым ответом",
                "переводные упражнения (для языков)",
            }
        )
    return _PLACEHOLDER_PHRASES


def _cyrillic_ratio(text: str) -> float:
    letters = [c for c in text if c.isalpha()]
    if not letters:
        return 0.0
    cyr = sum(1 for c in letters if "\u0400" <= c <= "\u04FF")
    return cyr / len(letters)


def is_latex_document(text: str) -> bool:
    if not text or len(text.strip()) < 40:
        return False
    t = text.strip()
    has_tasks = bool(
        re.search(r"\\begin\s*\{\s*task\s*\}", t, re.I)
        or (
            re.search(r"\\begin\s*\{\s*enumerate\s*\}", t, re.I)
            and re.search(r"\\item\b", t, re.I)
        )
    )
    return bool(
        re.search(r"\\documentclass", t, re.I)
        or re.search(r"\\begin\s*\{\s*document\s*\}", t, re.I)
        or (re.search(r"\\section\s*\{", t, re.I) and has_tasks)
    )


def _extract_task_bodies(latex: str) -> list[str]:
    from app.services.latex_convert import clean_latex_task_text, parse_latex_homework

    sections = parse_latex_homework(latex)
    if sections:
        out: list[str] = []
        for _, tasks in sections:
            out.extend(tasks)
        if out:
            return out
    raw = re.findall(
        r"\\begin\s*\{\s*task\s*\}(.*?)\\end\s*\{\s*task\s*\}",
        latex,
        re.DOTALL | re.IGNORECASE,
    )
    if raw:
        return [clean_latex_task_text(t) for t in raw if t.strip()]
    items = re.findall(
        r"\\item\s+(.+?)(?=\\item|\\end\s*\{\s*enumerate|\\section\s*\{|\Z)",
        latex,
        re.DOTALL | re.IGNORECASE,
    )
    return [clean_latex_task_text(t) for t in items if t.strip()]


def _normalize_task_key(text: str) -> str:
    return re.sub(r"\d+", "N", re.sub(r"\s+", " ", text.lower().strip()))


def is_placeholder_task(text: str) -> bool:
    """Задача — это заголовок типа из анкеты, а не условие."""
    t = re.sub(r"\s+", " ", text.lower().strip())
    if t in _placeholder_phrases():
        return True
    if len(t) < 55 and not re.search(r"\d", t) and "$" not in text and "\\" not in text:
        if any(
            kw in t
            for kw in (
                "упражнен",
                "тестов",
                "творческ",
                "выбором ответа",
                "открытым ответом",
                "текстовые задачи",
                "переводные",
            )
        ):
            return True
    return False


def is_ai_garbage_latex(latex: str) -> bool:
    """Модель вставила типы заданий / копирует одну секцию много раз."""
    tasks = _extract_task_bodies(latex)
    if not tasks:
        return True
    bad_tasks = sum(1 for t in tasks if is_placeholder_task(t))
    if bad_tasks >= max(2, len(tasks) // 2):
        return True

    titles = re.findall(r"\\section\s*\{([^}]*)\}", latex, re.I)
    if len(titles) >= 2:

        def _section_key(title: str) -> str:
            tl = title.lower().strip()
            if tl.startswith("памятка:"):
                return tl
            return tl

        keys = [_section_key(t) for t in titles]
        if len(keys) != len(set(keys)):
            return True
        if len(titles) >= 3 and len(set(keys)) == 1:
            return True
    return False


def is_repetitive_latex(latex: str) -> bool:
    """Один и тот же шаблон задачи копируется много раз (не «похожие» задачи по одной теме)."""
    tasks = _extract_task_bodies(latex)
    if len(tasks) < 5:
        return False
    keys = [_normalize_task_key(t) for t in tasks]
    top_count = Counter(keys).most_common(1)[0][1]
    if top_count >= max(5, int(len(tasks) * 0.7)):
        return True
    ratio = len(set(keys)) / len(keys)
    if len(tasks) >= 10 and ratio < 0.45:
        return True
    for phrase in ("среднее арифметическое", "найдите среднее", "найти среднее"):
        hits = sum(1 for t in tasks if phrase in t.lower())
        if hits >= 5 and hits / len(tasks) > 0.65:
            return True
    return False


def is_degenerate_latex(latex: str) -> bool:
    """Повтор одних и тех же задач / копия примера из промпта."""
    if is_ai_garbage_latex(latex):
        return True
    tasks = _extract_task_bodies(latex)
    if len(tasks) >= 2:
        normalized = [_normalize_task_key(t) for t in tasks]
        if len(set(normalized)) == 1:
            return True
    lower = latex.lower()
    echo_hits = sum(1 for m in PROMPT_ECHO_MARKERS if m.lower() in lower)
    if echo_hits >= 2 and len(tasks) >= 4:
        tasks_with_echo = sum(
            1 for t in tasks if any(m.lower() in t.lower() for m in PROMPT_ECHO_MARKERS)
        )
        if tasks_with_echo >= max(2, len(tasks) // 2):
            return True
    return False


def latex_validation_issues(text: str) -> list[str]:
    """Причины, по которым LaTeX не принят (для логов и отладки)."""
    issues: list[str] = []
    if not text or not text.strip():
        return ["пустой ответ"]
    if not is_latex_document(text):
        issues.append("нет \\documentclass / \\begin{document} / section+task")
    if _cyrillic_ratio(text) < MIN_CYRILLIC_RATIO:
        issues.append("мало кириллицы")
    tasks = _extract_task_bodies(text)
    if not tasks:
        issues.append("нет \\begin{task}")
    else:
        ph = sum(1 for t in tasks if is_placeholder_task(t))
        if ph >= max(1, len(tasks) // 3):
            issues.append(f"заглушки вместо задач ({ph}/{len(tasks)})")
    if is_ai_garbage_latex(text):
        issues.append("мусор или дубли секций")
    if is_repetitive_latex(text):
        issues.append("повторяющийся шаблон задач")
    if any(marker.lower() in text.lower() for marker in BAD_MARKERS):
        issues.append("служебные маркеры модели")
    return issues


def is_valid_latex_homework(text: str) -> bool:
    if not is_latex_document(text):
        return False
    if _cyrillic_ratio(text) < MIN_CYRILLIC_RATIO:
        return False
    if is_degenerate_latex(text):
        return False
    if any(marker.lower() in text.lower() for marker in BAD_MARKERS):
        return False
    tasks = _extract_task_bodies(text)
    if not tasks:
        return False
    if sum(1 for t in tasks if is_placeholder_task(t)) >= max(1, len(tasks) // 3):
        return False
    return True


def extract_html_fragment(text: str) -> str | None:
    text = text.strip()
    for pattern in (
        r"(<h2[\s>][\s\S]*?</(?:ul|ol)>)\s*",
        r"(<h2[\s>][\s\S]*?</h2>[\s\S]*?(?:</ul>|</ol>))",
        r"(<div>[\s\S]*?</div>)",
    ):
        m = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
        if m:
            return m.group(1).strip()
    if text.lstrip().startswith("<"):
        return text
    return None


def _plain_to_html(text: str) -> str:
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    if not lines:
        raise ValueError("empty")
    parts = ["<h2>Домашнее задание</h2>", "<ul>"]
    for ln in lines:
        ln = re.sub(r"^\d+[\).\s]+", "", ln)
        if ln:
            parts.append(f"<li>{ln}</li>")
    parts.append("</ul>")
    return "\n".join(parts)


def is_valid_homework_html(text: str) -> bool:
    if not text or len(text) < 60:
        return False
    lower = text.lower()
    if any(marker.lower() in lower for marker in BAD_MARKERS):
        return False
    if _cyrillic_ratio(text) < MIN_CYRILLIC_RATIO:
        return False
    if re.search(r"</li>", text, re.IGNORECASE):
        return True
    if re.search(r"<h[23][\s>]", text, re.IGNORECASE) and re.search(
        r"</(p|ul|ol)>", text, re.IGNORECASE
    ):
        return True
    return False


def sanitize_homework_response(
    raw: str, homework_prefs: dict | str | None = None
) -> str:
    """Сохраняем LaTeX; чистим задачи, убираем дубли; HTML — только если нет LaTeX."""
    from app.services.html_utils import ensure_html_fragment, extract_latex_document
    from app.services.homework_prefs import VOLUME_TASKS_PER_TOPIC, parse_homework_prefs
    from app.services.latex_convert import normalize_homework_latex_document, parse_latex_homework

    cleaned = extract_latex_document(raw)
    if is_latex_document(cleaned):
        prefs = parse_homework_prefs(homework_prefs)
        _, hi = VOLUME_TASKS_PER_TOPIC.get(prefs.get("volume", "standard"), ("6", "9"))
        cleaned = normalize_homework_latex_document(cleaned, max_per_topic=int(hi))
        lo, _ = VOLUME_TASKS_PER_TOPIC.get(prefs.get("volume", "standard"), ("6", "9"))

        sections = parse_latex_homework(cleaned)
        min_required = max(2, int(lo) - 3)
        total_tasks = sum(len(tasks) for _, tasks in sections) if sections else 0
        if sections and total_tasks < min_required:
            raise ValueError(
                f"Мало задач после очистки ({total_tasks} < {min_required})"
            )
        if is_ai_garbage_latex(cleaned):
            raise ValueError("Некачественный ответ модели (заглушки или дубли секций)")
    if is_valid_latex_homework(cleaned):
        return cleaned.strip()

    fragment = extract_html_fragment(cleaned)
    if not fragment and _cyrillic_ratio(cleaned) >= MIN_CYRILLIC_RATIO and len(cleaned) > 80:
        fragment = _plain_to_html(cleaned)
    if not fragment:
        fragment = ensure_html_fragment(cleaned)
    if is_valid_homework_html(fragment):
        return fragment
    raise ValueError("Модель вернула некорректный ответ")


def _strip_placeholder_tasks_from_latex(latex: str) -> str:
    """Удаляет \\begin{task} с заглушками (тип задания без условия)."""

    def repl(m: re.Match) -> str:
        body = m.group(1)
        return "" if is_placeholder_task(body) else m.group(0)

    return re.sub(
        r"\\begin\s*\{\s*task\s*\}(.*?)\\end\s*\{\s*task\s*\}",
        repl,
        latex,
        flags=re.DOTALL | re.IGNORECASE,
    )


def repair_ai_latex_document(
    raw: str, homework_prefs: dict | str | None = None
) -> str | None:
    """Чистка ответа Qwen без отбрасывания из‑за «похожих» задач по одной теме."""
    from app.services.html_utils import extract_latex_document
    from app.services.homework_prefs import VOLUME_TASKS_PER_TOPIC, parse_homework_prefs
    from app.services.latex_convert import normalize_homework_latex_document

    cleaned = extract_latex_document(raw)
    if not is_latex_document(cleaned):
        return None

    prefs = parse_homework_prefs(homework_prefs)
    lo, hi = VOLUME_TASKS_PER_TOPIC.get(prefs.get("volume", "standard"), ("6", "9"))
    min_tasks = max(2, int(lo) - 3)

    repaired = _strip_placeholder_tasks_from_latex(cleaned)
    repaired = normalize_homework_latex_document(repaired, max_per_topic=int(hi))
    good_tasks = [
        t
        for t in _extract_task_bodies(repaired)
        if not is_placeholder_task(t) and len(t.strip()) > 12
    ]
    if len(good_tasks) < min_tasks:
        logger.info("repair_ai_latex: мало задач %s < %s", len(good_tasks), min_tasks)
        return None
    if is_ai_garbage_latex(repaired):
        return None
    if any(marker.lower() in repaired.lower() for marker in BAD_MARKERS):
        return None
    if _cyrillic_ratio(repaired) < MIN_CYRILLIC_RATIO:
        return None
    return repaired.strip()


def can_lenient_accept_latex(latex: str, homework_prefs: dict | str | None = None) -> bool:
    """Минимальные требования: есть документ и несколько нормальных задач."""
    from app.services.homework_prefs import VOLUME_TASKS_PER_TOPIC, parse_homework_prefs

    if not is_latex_document(latex):
        return False
    prefs = parse_homework_prefs(homework_prefs)
    lo, _ = VOLUME_TASKS_PER_TOPIC.get(prefs.get("volume", "standard"), ("6", "9"))
    min_tasks = max(2, int(lo) - 4)
    good = [
        t
        for t in _extract_task_bodies(latex)
        if not is_placeholder_task(t) and len(t.strip()) > 10
    ]
    if len(good) < min_tasks:
        return False
    if is_ai_garbage_latex(latex):
        return False
    if any(marker.lower() in latex.lower() for marker in BAD_MARKERS):
        return False
    return _cyrillic_ratio(latex) >= MIN_CYRILLIC_RATIO


def force_accept_openrouter_latex(
    raw: str, homework_prefs: dict | str | None = None
) -> str | None:
    """Последний шанс: любой извлечённый .tex с documentclass."""
    from app.services.html_utils import extract_latex_document

    extracted = _strip_placeholder_tasks_from_latex(extract_latex_document(raw))
    if not extracted or len(extracted) < 60:
        return None
    if not (
        re.search(r"\\documentclass", extracted, re.I)
        or re.search(r"\\begin\s*\{\s*document\s*\}", extracted, re.I)
    ):
        return None
    if not re.search(
        r"\\begin\s*\{\s*task\s*\}|\\item\b|\\begin\s*\{\s*enumerate\s*\}",
        extracted,
        re.I,
    ):
        return None
    if not re.search(r"\\end\s*\{\s*document\s*\}", extracted, re.I):
        extracted = extracted.rstrip() + "\n\\end{document}\n"
    return extracted.strip()


def coerce_openrouter_latex(
    raw: str, homework_prefs: dict | str | None = None
) -> str:
    """
    Всегда сохраняем ответ OpenRouter, если в нём есть LaTeX-документ.
    ValueError — только если модель не вернула .tex вообще.
    """
    content, issues = accept_openrouter_latex(raw, homework_prefs=homework_prefs)
    if content:
        return content

    forced = force_accept_openrouter_latex(raw, homework_prefs)
    if forced:
        logger.warning("OpenRouter coerce: force (%s)", ", ".join(issues))
        return forced

    from app.services.html_utils import extract_latex_document

    tex = extract_latex_document(raw)
    if re.search(r"\\documentclass", tex, re.I) and len(tex) > 120:
        tex = _strip_placeholder_tasks_from_latex(tex)
        if not re.search(r"\\end\s*\{\s*document\s*\}", tex, re.I):
            tex = tex.rstrip() + "\n\\end{document}\n"
        logger.warning(
            "OpenRouter coerce: сырой .tex без проверки (%s)", ", ".join(issues)
        )
        return tex.strip()

    raise ValueError(
        "Модель не вернула LaTeX-документ"
        + (f": {'; '.join(issues)}" if issues else "")
    )


def accept_openrouter_latex(
    raw: str, homework_prefs: dict | str | None = None
) -> tuple[str | None, list[str]]:
    """
    Принять LaTeX от OpenRouter: строгая санитизация → починка → lenient → force.
    Возвращает (latex или None, список причин отказа).
    """
    try:
        strict = sanitize_homework_response(raw, homework_prefs=homework_prefs)
        if is_valid_latex_homework(strict):
            return strict, []
    except ValueError as e:
        logger.info("OpenRouter sanitize strict: %s", e)

    repaired = repair_ai_latex_document(raw, homework_prefs=homework_prefs)
    if repaired:
        return repaired, latex_validation_issues(repaired)

    from app.services.html_utils import extract_latex_document

    extracted = extract_latex_document(raw)
    if can_lenient_accept_latex(extracted, homework_prefs):
        logger.info(
            "OpenRouter: принят lenient LaTeX (%s задач)",
            len(_extract_task_bodies(extracted)),
        )
        return extracted.strip(), ["принято без строгой проверки"]

    forced = force_accept_openrouter_latex(raw, homework_prefs)
    if forced:
        logger.info(
            "OpenRouter: принят force LaTeX (%s задач)",
            len(_extract_task_bodies(forced)),
        )
        return forced, ["принято с минимальной проверкой"]

    return None, latex_validation_issues(extracted)


def needs_pdf_latex_rebuild(text: str) -> bool:
    """Битый LaTeX от модели — лучше пересобрать перед PDF."""
    if not text or len(text.strip()) < 30:
        return True
    if re.search(r"\\\[[\s\S]*?\\\]", text) and not re.search(
        r"\\begin\s*\{\s*task\s*\}", text, re.I
    ):
        return True
    if is_latex_document(text) and is_degenerate_latex(text):
        return True
    if is_latex_document(text) and is_ai_garbage_latex(text):
        return True
    if is_latex_document(text) and not is_valid_latex_homework(text):
        return True
    return False


def homework_content_to_html(content: str, *, render_math_images: bool = False) -> str:
    """LaTeX или HTML → HTML для превью и PDF."""
    from app.services.latex_convert import latex_document_to_html, normalize_homework_latex_document

    if not content or not content.strip():
        return content
    from app.services.latex_convert import normalize_math_delimiters

    if is_latex_document(content):
        content = normalize_homework_latex_document(content)
        normalized = normalize_math_delimiters(content)
        html = latex_document_to_html(normalized) or latex_document_to_html(content)
        if html:
            return process_homework_html(
                normalize_math_delimiters(html), render_images=render_math_images
            )
    if content.lstrip().startswith("<"):
        return process_homework_html(content, render_images=render_math_images)
    if _cyrillic_ratio(content) >= MIN_CYRILLIC_RATIO:
        return process_homework_html(_plain_to_html(content), render_images=render_math_images)
    return process_homework_html(f"<div>{content}</div>", render_images=render_math_images)


def process_homework_html(html: str, render_images: bool = True) -> str:
    from app.services.latex_convert import process_homework_html as _proc

    return _proc(html, render_images=render_images)
