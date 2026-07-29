"""Умный генератор ДЗ без нейросети — LaTeX и HTML."""

from html import escape


def _escape_latex_text(s: str) -> str:
    for ch, repl in (("&", r"\&"), ("%", r"\%"), ("#", r"\#"), ("_", r"\_")):
        s = s.replace(ch, repl)
    return s


def _difficulty_flags(understanding: int, difficulty: str) -> tuple[bool, bool]:
    hard = difficulty == "advanced" or understanding >= 4
    weak = understanding <= 2
    return weak, hard


def _log_tasks_plain(weak: bool, hard: bool) -> list[str]:
    if weak:
        return [
            "Вычисли: log₂(8), log₅(25), log₁₀(100).",
            "Примени свойство: log₃(27) + log₃(3).",
            "Найди ОДЗ функции y = log₂(x − 3).",
            "Реши: log₅(x) = 2.",
        ]
    if hard:
        return [
            "Реши: log₂(x+1) + log₂(x−1) = 3.",
            "Реши: 2·log₃(x) − log₃(9) = 1.",
            "Найди ОДЗ: y = log₅(4−x) / √(x+2).",
            "Сравни без вычисления: log₂(7) и log₂(5).",
        ]
    return [
        "Вычисли: log₃(81) и log₂(1/8).",
        "Упрости: log₄(2) + log₄(8).",
        "Найди ОДЗ: f(x) = log₀,₅(2x − 6).",
        "Реши: log₇(2x − 1) = 1.",
    ]


def _func_tasks_plain(weak: bool, hard: bool) -> list[str]:
    if weak:
        return [
            "Найди ОДЗ функции f(x) = 1/(x−2).",
            "Найди нули функции f(x) = x² − 9.",
            "Найди ОДЗ: g(x) = √(x+4).",
            "Найди нули: f(x) = 2x − 6.",
        ]
    if hard:
        return [
            "Найди ОДЗ и нули: f(x) = (x+1)/(x² − 4).",
            "При каких x функция f(x) = √(5−2x) определена?",
            "Найди нули и положительные значения: f(x) = x² − 5x + 6.",
            "Найди ОДЗ: f(x) = log₂(x−1) + 1/√(3−x).",
        ]
    return [
        "Найди ОДЗ: f(x) = 3/(x+5).",
        "Найди нули: f(x) = x² − 4x.",
        "Найди ОДЗ: f(x) = √(2x − 8).",
        "При каких x f(x) = 0, если f(x) = x² − 3x − 10?",
    ]


def _log_tasks_latex(weak: bool, hard: bool) -> list[str]:
    if weak:
        return [
            r"Вычислите: $\log_2 8$, $\log_5 25$, $\log_{10} 100$.",
            r"Примените свойство: $\log_3 27 + \log_3 3$.",
            r"Найдите ОДЗ: $y = \log_2 (x - 3)$.",
            r"Решите: $\log_5 x = 2$.",
        ]
    if hard:
        return [
            r"Решите: $\log_2(x+1) + \log_2(x-1) = 3$.",
            r"Решите: $2\log_3 x - \log_3 9 = 1$.",
            r"Найдите ОДЗ: $y = \dfrac{\log_5(4-x)}{\sqrt{x+2}}$.",
            r"Сравните без вычисления: $\log_2 7$ и $\log_2 5$.",
        ]
    return [
        r"Вычислите: $\log_3 81$ и $\log_2 \frac{1}{8}$.",
        r"Упростите: $\log_4 2 + \log_4 8$.",
        r"Найдите ОДЗ: $f(x) = \log_{0.5}(2x - 6)$.",
        r"Решите: $\log_7(2x - 1) = 1$.",
    ]


def _func_tasks_latex(weak: bool, hard: bool) -> list[str]:
    if weak:
        return [
            r"Найдите ОДЗ функции $f(x) = \dfrac{1}{x-2}$.",
            r"Найдите нули функции $f(x) = x^2 - 9$.",
            r"Найдите ОДЗ: $g(x) = \sqrt{x+4}$.",
            r"Найдите нули: $f(x) = 2x - 6$.",
        ]
    if hard:
        return [
            r"Найдите ОДЗ и нули: $f(x) = \dfrac{x+1}{x^2 - 4}$.",
            r"При каких $x$ функция $f(x) = \sqrt{5-2x}$ определена?",
            r"Найдите нули и положительные значения: $f(x) = x^2 - 5x + 6$.",
            r"Найдите ОДЗ: $f(x) = \log_2(x-1) + \dfrac{1}{\sqrt{3-x}}$.",
        ]
    return [
        r"Найдите ОДЗ: $f(x) = \dfrac{3}{x+5}$.",
        r"Найдите нули: $f(x) = x^2 - 4x$.",
        r"Найдите ОДЗ: $f(x) = \sqrt{2x - 8}$.",
        r"При каких $x$ $f(x) = 0$, если $f(x) = x^2 - 3x - 10$?",
    ]


def _generic_tasks_plain(weak: bool, hard: bool) -> list[str]:
    if weak:
        return [
            "Вычисли: 48 : 6 + 7.",
            "Реши: 2x + 5 = 17.",
            "Упрости: 3(x − 2) + 2x.",
            "Задача: сумма двух чисел 25, одно на 7 больше другого. Найди числа.",
        ]
    if hard:
        return [
            "Реши: 3x² − 12 = 0.",
            "Задача: периметр прямоугольника 34 см, длина на 5 см больше ширины. Найди стороны.",
            "Упрости: (2x − 1)² − (x + 3)(x − 3).",
            "При каких x выражение 5/(x−1) имеет смысл?",
        ]
    return [
        "Реши: 4x − 9 = 15.",
        "Вычисли: 3/5 + 1/10.",
        "Найди 20% от 150.",
        "Задача: в 3 одинаковых коробках 24 карандаша. Сколько в 5 таких коробках?",
    ]


def _generic_tasks_latex(weak: bool, hard: bool) -> list[str]:
    if weak:
        return [
            r"Вычислите: $48 : 6 + 7$.",
            r"Решите: $2x + 5 = 17$.",
            r"Упростите: $3(x - 2) + 2x$.",
            r"Сумма двух чисел $25$, одно на $7$ больше другого. Найдите числа.",
        ]
    if hard:
        return [
            r"Решите: $3x^2 - 12 = 0$.",
            r"Периметр прямоугольника $34$ см, длина на $5$ см больше ширины. Найдите стороны.",
            r"Упростите: $(2x - 1)^2 - (x + 3)(x - 3)$.",
            r"При каких $x$ выражение $\dfrac{5}{x-1}$ имеет смысл?",
        ]
    return [
        r"Решите: $4x - 9 = 15$.",
        r"Вычислите: $\frac{3}{5} + \frac{1}{10}$.",
        r"Найдите $20\%$ от $150$.",
        r"В $3$ одинаковых коробках $24$ карандаша. Сколько в $5$ таких коробках?",
    ]


def _topic_has_log(t: str) -> bool:
    return "логарифм" in t or "логоритм" in t


def _topic_has_functions(t: str) -> bool:
    return (
        "функци" in t
        or "одз" in t
        or "нули" in t
        or "область определения" in t
        or "область опред" in t
    )


def _tasks_for_topic(topic: str, understanding: int, difficulty: str) -> list[str]:
    t = topic.lower()
    weak, hard = _difficulty_flags(understanding, difficulty)

    collected: list[str] = []
    if _topic_has_functions(t):
        collected.extend(_func_tasks_plain(weak, hard))
    if _topic_has_log(t):
        collected.extend(_log_tasks_plain(weak, hard))
    if collected:
        return collected

    if "дроб" in t:
        if weak:
            return [
                "Найди общий знаменатель для пар: 1/2 и 1/4; 2/3 и 1/6. Запиши преобразование.",
                "Сложи: 1/5 + 2/5. Сложи: 3/8 + 1/8. Покажи каждый шаг.",
                "Реши: 2/3 - 1/6. Проверь ответ подстановкой.",
                "Из текста: «Съели 2/5 пирога, потом ещё 1/5» — какая часть съедена всего?",
            ]
        if hard:
            return [
                "Сложи: 2/3 + 5/6. Сложи: 7/12 + 1/8 (приведи к общему знаменателю).",
                "Реши: 5/6 - 1/4 + 1/3. Оформи пошаговое решение.",
                "Задача: бак заполнен на 3/4, вылили 1/6. Какая часть осталась?",
                "Сравни: 5/8 и 2/3. Объясни, какой способ сравнения использовал.",
            ]
        return [
            "Сложи: 1/4 + 3/4. Сложи: 2/5 + 1/10.",
            "Реши: 5/6 - 1/3. Реши: 1/2 + 1/3.",
            "Задача: ученик прочитал 2/7 книги в понедельник и 3/7 во вторник. Сколько всего?",
            "Составь 2 примера на сложение дробей с разными знаменателями.",
        ]

    if "уравн" in t or "x" in t:
        if weak:
            return [
                "Реши: x + 5 = 12. Реши: x − 3 = 7.",
                "Реши: 2x = 14. Проверь корень подстановкой.",
                "Составь уравнение по фразе: «Число увеличили на 4 и получили 15».",
            ]
        return [
            "Реши: 3x + 2 = 17. Реши: 2x − 5 = 9.",
            "Реши: 4(x + 1) = 20. Покажи два шага преобразования.",
            "Задача: сумма двух чисел 48, одно в 3 раза больше другого. Найди числа.",
        ]

    return _generic_tasks_plain(weak, hard)


def _tasks_latex_for_topic(topic: str, understanding: int, difficulty: str) -> list[str]:
    """Задания с формулами в $...$ для LaTeX-документа."""
    t = topic.lower()
    weak, hard = _difficulty_flags(understanding, difficulty)

    collected: list[str] = []
    if _topic_has_functions(t):
        collected.extend(_func_tasks_latex(weak, hard))
    if _topic_has_log(t):
        collected.extend(_log_tasks_latex(weak, hard))
    if collected:
        return collected

    if "дроб" in t:
        if weak:
            return [
                r"Найдите общий знаменатель: $\frac{1}{2}$ и $\frac{1}{4}$; $\frac{2}{3}$ и $\frac{1}{6}$.",
                r"Вычислите: $\frac{1}{5}+\frac{2}{5}$ и $\frac{3}{8}+\frac{1}{8}$.",
                r"Решите: $\frac{2}{3}-\frac{1}{6}$. Проверьте ответ.",
                r"Задача: съели $\frac{2}{5}$ пирога, затем $\frac{1}{5}$. Какая часть съедена?",
            ]
        if hard:
            return [
                r"Вычислите: $\frac{2}{3}+\frac{5}{6}$ и $\frac{7}{12}+\frac{1}{8}$.",
                r"Решите: $\frac{5}{6}-\frac{1}{4}+\frac{1}{3}$.",
                r"Бак заполнен на $\frac{3}{4}$, вылили $\frac{1}{6}$. Какая часть осталась?",
                r"Сравните $\frac{5}{8}$ и $\frac{2}{3}$.",
            ]
        return [
            r"Вычислите: $\frac{1}{4}+\frac{3}{4}$ и $\frac{2}{5}+\frac{1}{10}$.",
            r"Решите: $\frac{5}{6}-\frac{1}{3}$ и $\frac{1}{2}+\frac{1}{3}$.",
            r"Прочитали $\frac{2}{7}$ книги в пн и $\frac{3}{7}$ во вт. Сколько всего?",
            r"Составьте 2 примера на сложение дробей с разными знаменателями.",
        ]

    if "квадрат" in t or "уравн" in t:
        if weak:
            return [
                r"Решите: $x+5=12$ и $x-3=7$.",
                r"Решите: $2x=14$. Проверьте корень подстановкой.",
                r"Решите: $x^2-9=0$. Запишите оба корня.",
                r"Составьте квадратное уравнение с корнями $2$ и $-2$.",
            ]
        if hard:
            return [
                r"Решите: $x^2-5x+6=0$.",
                r"При каком $a$ уравнение $2x^2+ax+3=0$ имеет один корень?",
                r"Решите: $3x^2-12=0$.",
                r"Задача: площадь прямоугольника $S=x(10-x)$. При каком $x$ площадь максимальна?",
            ]
        return [
            r"Решите: $x^2-4=0$.",
            r"Разложите на множители: $x^2+5x+6$.",
            r"Решите: $2x^2-8=0$.",
            r"Решите: $x^2+2x-8=0$.",
        ]

    if "средн" in t and ("арифмет" in t or "числ" in t):
        sets = [
            (2, 4, 6, 8, 10),
            (3, 5, 7, 9, 11),
            (1, 3, 5, 7, 9),
            (4, 6, 8, 10, 12),
            (5, 10, 15, 20, 25),
            (12, 15, 18, 21, 24),
        ]
        if weak:
            return [
                f"Найдите среднее арифметическое чисел {sets[0]}.",
                f"Найдите среднее арифметическое чисел {sets[1]}.",
                "Запишите формулу среднего арифметического для $n$ чисел $a_1,\\ldots,a_n$.",
                f"Температура за 3 дня: $12^\\circ$, $15^\\circ$, $18^\\circ$. Найдите среднюю.",
            ]
        if hard:
            return [
                f"Среднее чисел {sets[2]} равно $5$. Какое число нужно добавить, чтобы среднее стало $6$?",
                f"Среднее {sets[3]} — найдите, на сколько нужно увеличить каждое число, чтобы среднее выросло на $2$.",
                "В классе 5 оценок со средним $4{,}2$. Какая минимальная шестая оценка даст среднее не ниже $4{,}5$?",
                f"Сравните средние наборов {sets[4]} и {sets[5]}. Объясните вывод.",
            ]
        return [
            f"Найдите среднее арифметическое чисел {sets[0]}.",
            f"Найдите среднее арифметическое чисел {sets[1]}.",
            f"Среднее чисел {sets[2]} равно $5$. Какое из них наибольшее?",
            f"Задача: за неделю пробежали $3$, $5$, $7$, $9$, $11$ км. Сколько км в среднем за день?",
            f"Добавьте к числам {sets[3]} число $14$ и найдите новое среднее.",
            f"Среднее $4$ чисел равно $8$. Найдите сумму этих чисел.",
        ]

    if "тригоном" in t or "неравен" in t or "sin" in t or "cos" in t:
        if weak:
            return [
                r"На окружности отметьте углы $30^\circ$, $45^\circ$, $60^\circ$. Запишите $\sin$ и $\cos$.",
                r"Решите на $[0; 2\pi]$: $\sin x \geq \frac{1}{2}$.",
                r"Решите: $\cos x < 0$ на $[0; 2\pi]$.",
                r"Упростите: $\sin^2 x + \cos^2 x$ при $x = \frac{\pi}{4}$.",
            ]
        if hard:
            return [
                r"Решите: $\sin 2x > \cos x$ на $[0; 2\pi]$.",
                r"Решите: $2\cos^2 x - 3\cos x + 1 \leq 0$.",
                r"Найдите число решений: $\tan x = \sqrt{3}$ на $[0; 2\pi]$.",
                r"Решите: $\sin x + \sin 2x = 0$ на $[-\pi; \pi]$.",
            ]
        return [
            r"Решите на $[0; 2\pi]$: $\sin x > \frac{\sqrt{2}}{2}$.",
            r"Решите: $\cos 2x \leq \frac{1}{2}$.",
            r"Решите: $\tan x = 1$ на $[0; 2\pi]$.",
            r"Решите: $2\sin x - 1 = 0$.",
            r"Запишите формулу приведения для $\sin(\pi - x)$.",
            r"Решите: $\sin x \cdot \cos x < 0$ на $(0; 2\pi)$.",
        ]

    if "иррацион" in t or "корн" in t:
        if weak:
            return [
                r"Упростите: $\sqrt{16}$ и $\sqrt{25}$.",
                r"Решите: $\sqrt{x}=3$, $x\geq 0$.",
                r"Вычислите: $\sqrt{2}\cdot\sqrt{8}$.",
            ]
        return [
            r"Решите: $\sqrt{2x+1}=5$.",
            r"Решите: $\sqrt{x-1}=2$.",
            r"Найдите ОДЗ: $\sqrt{5-x}$.",
            r"Решите: $\sqrt{x}+\sqrt{x}=4$.",
        ]

    return _generic_tasks_latex(weak, hard)


def _max_tasks_per_topic(volume: str) -> int:
    return {"minimal": 4, "standard": 6, "extended": 12}.get(volume, 6)


def generate_smart_homework_latex(
    student_name: str,
    subject: str,
    checklist: list[dict],
    grade: str = "",
    homework_prefs: dict | None = None,
) -> str:
    """Полный LaTeX-документ — надёжный fallback и эталон формата."""
    from app.services.homework_prefs import parse_homework_prefs

    from app.services.homework_prefs import apply_prefs_to_checklist

    prefs = parse_homework_prefs(homework_prefs)
    checklist = apply_prefs_to_checklist(checklist, prefs, force=True)
    max_tasks = _max_tasks_per_topic(prefs.get("volume", "standard"))
    subj = _escape_latex_text(subject)
    name = _escape_latex_text(student_name)
    lines = [
        r"\documentclass[a4paper,12pt]{article}",
        r"\usepackage[T1,T2A]{fontenc}",
        r"\usepackage[utf8]{inputenc}",
        r"\usepackage[russian]{babel}",
        r"\usepackage{amsmath,amssymb}",
        r"\usepackage{geometry}",
        r"\geometry{top=2cm, bottom=2cm, left=2.5cm, right=2.5cm}",
        r"\newenvironment{task}{\par\noindent}{\par\medskip}",
        r"\begin{document}",
        f"\\title{{Домашнее задание по {subj}}}",
        f"\\author{{Ученик: {name}}}",
        r"\date{\today}",
        r"\maketitle",
    ]
    for item in checklist:
        topic = _escape_latex_text(item["topic"])
        u = int(item.get("understanding", 3))
        diff = item.get("difficulty", "medium")
        lines.append(f"\\section{{{topic}}}")
        if prefs.get("include_cheatsheet"):
            lines.append(
                f"\\begin{{task}} Памятка: кратко повтори ключевые правила по теме «{topic}». \\end{{task}}"
            )
        tasks = _tasks_latex_for_topic(item["topic"], u, diff)[:max_tasks]
        for task in tasks:
            hint = " (подсказка: начни с определения)" if prefs.get("include_hints") and u <= 3 else ""
            lines.append(f"\\begin{{task}} {task}{hint} \\end{{task}}")
    lines.append(r"\end{document}")
    return "\n".join(lines)


def generate_smart_homework(
    student_name: str,
    subject: str,
    checklist: list[dict],
    grade: str = "",
) -> str:
    parts = [
        "<h2>Домашнее задание</h2>",
        f"<p><strong>Ученик:</strong> {escape(student_name)} · "
        f"<strong>Предмет:</strong> {escape(subject)}"
        + (f" · <strong>Класс:</strong> {escape(grade)}" if grade else "")
        + "</p>",
    ]
    for i, item in enumerate(checklist, 1):
        topic = item["topic"]
        u = int(item.get("understanding", 3))
        diff = item.get("difficulty", "medium")
        parts.append(f"<h3>Блок {i}. {escape(topic)}</h3>")
        parts.append(f"<p><em>На уроке понимание: {u}/5</em></p>")
        parts.append("<ol>")
        for task in _tasks_for_topic(topic, u, diff):
            parts.append(f"<li>{escape(task)}</li>")
        parts.append("</ol>")
    parts.append(
        "<p><strong>Срок:</strong> к следующему занятию. "
        "Если застрял — отметь номер задачи, разберём на уроке.</p>"
    )
    return "\n".join(parts)
