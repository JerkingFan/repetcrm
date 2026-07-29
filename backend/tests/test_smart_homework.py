"""Умный шаблон ДЗ — конкретные задачи, не мета-инструкции."""

from app.services.smart_homework import (
    _tasks_for_topic,
    _tasks_latex_for_topic,
    generate_smart_homework_latex,
)


def test_functions_and_log_topic_has_concrete_tasks():
    topic = "Повторение, функции(область определения, нули функции) + Логарифм"
    tasks = _tasks_for_topic(topic, understanding=2, difficulty="medium")
    assert tasks
    joined = " ".join(tasks).lower()
    assert "кратко запиши определения" not in joined
    assert "типичные ошибки" not in joined
    assert "одз" in joined or "нули" in joined
    assert "log" in joined


def test_latex_functions_and_log_topic():
    topic = "Повторение, функции(область определения, нули функции) + Логарифм"
    tasks = _tasks_latex_for_topic(topic, understanding=2, difficulty="medium")
    assert len(tasks) >= 6
    joined = " ".join(tasks)
    assert r"\log" in joined
    assert "ОДЗ" in joined or "нули" in joined


def test_unknown_topic_no_meta_instructions():
    tasks = _tasks_for_topic("Квантовая механика", understanding=2, difficulty="medium")
    joined = " ".join(tasks).lower()
    assert "кратко запиши" not in joined
    assert "типичные ошибки" not in joined
    assert any(ch.isdigit() for t in tasks for ch in t)


def test_generate_latex_document_for_log_functions():
    latex = generate_smart_homework_latex(
        "Иван",
        "Математика",
        [
            {
                "topic": "функции + логарифм",
                "understanding": 2,
                "difficulty": "medium",
            }
        ],
    )
    assert r"\documentclass" in latex
    assert r"\begin{task}" in latex
    assert "кратко запиши" not in latex.lower()
