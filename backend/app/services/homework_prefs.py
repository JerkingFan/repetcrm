"""Настройки ДЗ репетитора → промпт и чек-лист."""

import json
from typing import Any

DEFAULT_HOMEWORK_PREFS: dict[str, Any] = {
    "focus_aspect": "mixed",
    "student_level": "medium",
    "understanding_global": 3,
    "task_types": ["practice_rules", "text_problems"],
    "volume": "standard",
    "difficulty_level": "medium",
    "special_notes": "",
    "output_formats": ["latex"],
    "include_cheatsheet": False,
    "include_hints": False,
    "include_examples": False,
}

FOCUS_ASPECT_LABELS = {
    "theory": "Теория (правила, формулы, концепции)",
    "practice": "Практика (задачи, упражнения)",
    "mixed": "Смешанный формат",
    "errors_review": "Разбор ошибок / работа над пробелами",
}

STUDENT_LEVEL_LABELS = {
    "beginner": "Начинающий",
    "medium": "Средний",
    "advanced": "Продвинутый",
    "exam": "Подготовка к экзамену (ОГЭ, ЕГЭ, IELTS и т.д.)",
}

TASK_TYPE_LABELS = {
    "practice_rules": "Упражнения на отработку формул/правил",
    "text_problems": "Текстовые задачи",
    "tests": "Тестовые задания",
    "creative": "Творческие задания",
    "multiple_choice": "Задания с выбором ответа",
    "open_answer": "Задания с открытым ответом",
    "translation": "Переводные упражнения (для языков)",
}

VOLUME_LABELS = {
    "minimal": "Минимальный (3–5 заданий на тему, ~15–20 мин)",
    "standard": "Стандартный (6–9 заданий, ~30–40 мин)",
    "extended": "Расширенный (12+ заданий, ~60+ мин)",
}

DIFFICULTY_LABELS = {
    "basic": "Базовый — закрепление пройденного",
    "medium": "Средний — 1–2 задания повышенной сложности",
    "high": "Высокий — нестандартные, олимпиадные",
}

OUTPUT_FORMAT_LABELS = {
    "pdf": "PDF для печати",
    "chat_text": "Текст для копирования в чат",
    "latex": "LaTeX (математические формулы)",
    "html": "HTML для платформы",
}

VOLUME_TASKS_PER_TOPIC = {
    "minimal": ("3", "5"),
    "standard": ("6", "9"),
    "extended": ("12", "15"),
}

WORK_TYPE_FROM_FOCUS = {
    "theory": "theory",
    "practice": "practice",
    "mixed": "practice",
    "errors_review": "test",
}

DIFFICULTY_FROM_LEVEL = {
    "basic": "basic",
    "medium": "medium",
    "high": "advanced",
}


def parse_homework_prefs(raw: str | dict | None) -> dict[str, Any]:
    if isinstance(raw, dict):
        merged = dict(DEFAULT_HOMEWORK_PREFS)
        merged.update(raw)
        return merged
    if not raw or not str(raw).strip():
        return dict(DEFAULT_HOMEWORK_PREFS)
    try:
        data = json.loads(raw)
        if not isinstance(data, dict):
            return dict(DEFAULT_HOMEWORK_PREFS)
    except json.JSONDecodeError:
        return dict(DEFAULT_HOMEWORK_PREFS)
    merged = dict(DEFAULT_HOMEWORK_PREFS)
    merged.update(data)
    return merged


def serialize_homework_prefs(prefs: dict[str, Any]) -> str:
    base = dict(DEFAULT_HOMEWORK_PREFS)
    base.update(prefs)
    return json.dumps(base, ensure_ascii=False)


def _labels_list(keys: list[str], mapping: dict[str, str]) -> str:
    if not keys:
        return "—"
    return ", ".join(mapping.get(k, k) for k in keys)


def apply_prefs_to_checklist(
    checklist: list[dict],
    prefs: dict[str, Any] | str | None,
    *,
    force: bool = True,
) -> list[dict]:
    """Синхронизирует строки тем с глобальными настройками формы."""
    p = parse_homework_prefs(prefs)
    default_wt = WORK_TYPE_FROM_FOCUS.get(p.get("focus_aspect", "mixed"), "practice")
    default_diff = DIFFICULTY_FROM_LEVEL.get(p.get("difficulty_level", "medium"), "medium")
    global_u = int(p.get("understanding_global", 3))

    out = []
    for item in checklist:
        row = dict(item)
        if force or not row.get("work_type"):
            row["work_type"] = default_wt
        if force or not row.get("difficulty"):
            row["difficulty"] = default_diff
        row["understanding"] = global_u
        out.append(row)
    return out


def format_checklist_for_prompt(checklist: list[dict]) -> str:
    work_type_ru = {"theory": "теория", "practice": "практика", "test": "тест"}
    difficulty_ru = {"basic": "базовая", "medium": "средняя", "advanced": "продвинутая"}
    lines = []
    for i, item in enumerate(checklist, 1):
        wt = work_type_ru.get(item.get("work_type", "practice"), item.get("work_type"))
        diff = difficulty_ru.get(item.get("difficulty", "medium"), item.get("difficulty"))
        u = item.get("understanding", 3)
        lines.append(
            f"{i}. Тема: «{item['topic']}»; на уроке: {wt}; сложность: {diff}; усвоение: {u}/5"
        )
    return "\n".join(lines) if lines else "— темы не указаны —"


def _understanding_rules(u: int, include_hints: bool) -> str:
    if u >= 4:
        base = (
            "Усвоение 4–5: обязательно включи заметную долю задач повышенной сложности; "
            "минимум одна нестандартная задача на тему."
        )
    elif u <= 2:
        base = (
            "Усвоение 1–2: преобладать должны базовые упражнения пошагового типа; "
            "избегай олимпиадных и многошаговых задач без подсказок."
        )
    else:
        base = "Усвоение 3: баланс базовых и средних задач."
    if include_hints and u <= 3:
        base += " Добавь краткие подсказки внутри формулировок сложных задач."
    return base


def _student_level_rules(level: str) -> str:
    rules = {
        "beginner": "Уровень начинающий: простые формулировки, малые числа, без лишних усложнений.",
        "medium": "Уровень средний: стандартные школьные/курсовые задачи.",
        "advanced": "Уровень продвинутый: можно давать нестандартные и комбинированные задачи.",
        "exam": (
            "Подготовка к экзамену: ориентируйся на формат экзаменационных заданий "
            "(часть А/Б, тесты, эссе — по предмету), укажи типовые ловушки."
        ),
    }
    return rules.get(level, rules["medium"])


def _task_types_rules(task_types: list[str]) -> str:
    if not task_types:
        return "Типы заданий: любые уместные по теме."
    lines = [
        "Нужны такие ТИПЫ заданий (распредели по темам):",
        "ЗАПРЕЩЕНО вставлять в \\begin{task} только название типа — нужно полное условие с числами/формулами.",
    ]
    for key in task_types:
        lines.append(f"  • {TASK_TYPE_LABELS.get(key, key)}")
    lines.append("Не добавляй типы вне этого списка, если репетитор не указал иное в пожеланиях.")
    return "\n".join(lines)


LATEX_ONLY_OUTPUT_RULES = """
КРИТИЧНО — ФОРМАТ ОТВЕТА (нарушение = отказ системы):
• Выводи ИСКЛЮЧИТЕЛЬНО LaTeX code: сырой текст .tex, без обёрток и без комментариев вне документа.
• Первый символ ответа: обратный слэш в \\documentclass (не пробел, не «Вот», не #, не ```).
• Последняя строка: \\end{document} — после неё НИЧЕГО (ни пояснений, ни «Удачи», ни markdown).
• ЗАПРЕЩЕНО: ```latex```, ``` , markdown (#, **), HTML, JSON, «конечно», «вот задание», списки вне LaTeX.
• ЗАПРЕЩЕНО: \\boxed, решения, ответы, «Правильный ответ», пошаговые решения (только условия задач).
• Каждая задача — отдельный \\begin{task} ... \\end{task} с ПОЛНЫМ условием на русском и формулами в $...$.
• Внутри task: без \\textbf, без «Задача 1», без заголовков типа «Упражнения на отработку» — только математическое условие.
• Не копируй примеры из этого промпта (x^2-5x+6, 2x^2+ax+3) — придумай свои числа и сюжеты по теме.
• Не повторяй одну и ту же фразу с подстановкой других чисел; не дублируй \\section с одним названием.
• Не вставляй в task только название типа задания — нужны числа, данные, формулы.
""".strip()


def _latex_structure_rules(p: dict[str, Any]) -> str:
    parts = [
        LATEX_ONLY_OUTPUT_RULES,
        "Структура: \\documentclass{article} → преамбула → \\begin{document} → \\maketitle → "
        "\\section{Тема} → несколько \\begin{task}...\\end{task} → \\end{document}.",
        "Все математические выражения только в $...$ (дроби: $\\frac{a}{b}$, тригонометрия: $\\sin x$).",
    ]
    if p.get("include_cheatsheet"):
        parts.append(
            "По желанию: отдельная короткая \\section{Памятка: <тема>} (формулы/правила), "
            "затем \\section{<тема>} с задачами. Памятка — не дублируй её 2+ раз."
        )
    if p.get("include_examples"):
        parts.append(
            "Для 1–2 самых сложных задач на тему добавь отдельный блок "
            "\\begin{task} Пример (не для сдачи): ... \\end{task} с полным образцом решения."
        )
    if p.get("include_hints") and not p.get("include_examples"):
        parts.append("В условиях сложных задач добавляй короткие подсказки в скобках.")
    if not p.get("include_cheatsheet") and not p.get("include_hints") and not p.get("include_examples"):
        parts.append("Только условия задач, без памяток, подсказок и готовых решений.")
    return "\n".join(parts)


def build_system_prompt_for_homework(prefs: dict[str, Any] | str | None) -> str:
    p = parse_homework_prefs(prefs)
    lo, hi = VOLUME_TASKS_PER_TOPIC.get(p.get("volume", "standard"), ("6", "9"))
    return (
        "Ты генератор LaTeX-документов для домашних заданий репетитора. "
        "Ты НЕ чат-ассистент: не здоровайся, не объясняй, не спрашивай уточнений. "
        f"Объём: ровно {lo}–{hi} блоков \\begin{{task}} на КАЖДУЮ тему из списка пользователя. "
        f"Сложность: {DIFFICULTY_LABELS.get(p.get('difficulty_level', 'medium'), '')}. "
        f"Типы заданий: {_labels_list(p.get('task_types') or [], TASK_TYPE_LABELS)}. "
        "Единственный допустимый вывод — валидный LaTeX code от \\documentclass до \\end{document}, "
        "без markdown и без текста вне документа."
    )


def build_user_prompt_for_homework(
    student_name: str,
    subject: str,
    checklist: list[dict],
    grade: str = "",
    homework_prefs: dict[str, Any] | str | None = None,
) -> str:
    p = parse_homework_prefs(homework_prefs)
    checklist_merged = apply_prefs_to_checklist(checklist, p, force=True)
    topics_block = format_checklist_for_prompt(checklist_merged)
    lo, hi = VOLUME_TASKS_PER_TOPIC.get(p.get("volume", "standard"), ("6", "9"))
    grade_line = f"\nКласс ученика: {grade}." if grade else ""
    u = int(p.get("understanding_global", 3))

    return f"""Ты — репетитор по предмету «{subject}». Ученик: {student_name}.{grade_line}

=== ДАННЫЕ С ЗАНЯТИЯ (обязательно учти) ===
{topics_block}

=== НАСТРОЙКИ РЕПЕТИТОРА (приоритет над общими шаблонами) ===
• Фокус урока: {FOCUS_ASPECT_LABELS.get(p.get("focus_aspect", "mixed"), "")}
• Понимание на уроке: {u}/5 — {_understanding_rules(u, p.get("include_hints"))}
• Уровень ученика: {_student_level_rules(p.get("student_level", "medium"))}
• Объём ДЗ: {VOLUME_LABELS.get(p.get("volume", "standard"), "")} → ровно {lo}–{hi} задач \\begin{{task}} на КАЖДУЮ тему
• Сложность заданий: {DIFFICULTY_LABELS.get(p.get("difficulty_level", "medium"), "")}
{_task_types_rules(p.get("task_types") or [])}
• Памятка по теме: {"ДА" if p.get("include_cheatsheet") else "НЕТ"}
• Подсказки в задачах: {"ДА" if p.get("include_hints") else "НЕТ"}
• Примеры решений: {"ДА" if p.get("include_examples") else "НЕТ"}
• Особые пожелания репетитора: {p.get("special_notes").strip() or "нет"}

=== ФОРМАТ ВЫВОДА (ОБЯЗАТЕЛЬНО) ===
{_latex_structure_rules(p)}

Начни ответ сразу с \\documentclass — без вступления.
Заверши на \\end{{document}} — без заключения.
Повтор: ТОЛЬКО LaTeX code, иначе задание будет отброшено.

Шаблон документа (заполни секции и task; не отдавай пустой шаблон):
\\documentclass[a4paper,12pt]{{article}}
\\usepackage[T1,T2A]{{fontenc}}
\\usepackage[utf8]{{inputenc}}
\\usepackage[russian]{{babel}}
\\usepackage{{amsmath,amssymb}}
\\usepackage{{geometry}}
\\geometry{{top=2cm, bottom=2cm, left=2.5cm, right=2.5cm}}
\\newenvironment{{task}}{{\\par\\noindent}}{{\\par\\medskip}}
\\begin{{document}}
\\title{{Домашнее задание по {subject}}}
\\author{{Ученик: {student_name}}}
\\date{{\\today}}
\\maketitle
% \\section{{Название темы}} + задачи
\\end{{document}}

Сгенерируй полный LaTeX-документ по настройкам выше.
Выведи ТОЛЬКО LaTeX code (от \\documentclass до \\end{{document}}), без markdown и без текста снаружи.
Задачи уникальные, с разными формулировками, строго по каждой теме из чек-листа."""


# Обратная совместимость
def format_additional_requirements(prefs: dict[str, Any] | str | None) -> str:
    p = parse_homework_prefs(prefs)
    lo, hi = VOLUME_TASKS_PER_TOPIC.get(p.get("volume", "standard"), ("6", "9"))
    return (
        f"Объём: {lo}–{hi} задач/тема; "
        f"типы: {_labels_list(p.get('task_types') or [], TASK_TYPE_LABELS)}; "
        f"сложность: {DIFFICULTY_LABELS.get(p.get('difficulty_level', 'medium'), '')}"
    )
