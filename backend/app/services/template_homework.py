"""Офлайн-генератор без нейросети — запасной вариант, если Ollama недоступна."""

from html import escape


def generate_template_homework(
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
        "<p><em>Собрано автоматически по чек-листу урока. "
        "Для текста от нейросети: Настройки → AI или установите Ollama.</em></p>",
    ]
    for i, item in enumerate(checklist, 1):
        topic = escape(item["topic"])
        wt = {"theory": "Теория", "practice": "Практика", "test": "Тест"}.get(
            item.get("work_type", "practice"), "Практика"
        )
        diff = {"basic": "базовый", "medium": "средний", "advanced": "продвинутый"}.get(
            item.get("difficulty", "medium"), "средний"
        )
        u = int(item.get("understanding", 3))
        parts.append(f"<h3>Задание {i}. {topic}</h3>")
        parts.append(f"<p>Формат: {wt}, уровень: {diff}, понимание на уроке: {u}/5.</p>")
        if u <= 2:
            parts.append(
                "<ul>"
                f"<li>Повтори определения и правила по теме «{topic}».</li>"
                f"<li>Реши 3 простых примера с пошаговым решением.</li>"
                f"<li>Запиши, что осталось непонятным — обсудим на следующем уроке.</li>"
                "</ul>"
            )
        elif u == 3:
            parts.append(
                "<ul>"
                f"<li>Кратко законспектируй тему «{topic}».</li>"
                f"<li>Выполни 4 упражнения средней сложности.</li>"
                f"<li>Проверь себя по ответам в учебнике или конспекту.</li>"
                "</ul>"
            )
        else:
            parts.append(
                "<ul>"
                f"<li>Подготовь 2 задачи повышенной сложности по теме «{topic}».</li>"
                f"<li>Объясни решение одной из задач письменно.</li>"
                f"<li>Придумай 1 похожий пример самостоятельно.</li>"
                "</ul>"
            )
    parts.append("<p><strong>Срок:</strong> к следующему занятию.</p>")
    return "\n".join(parts)
